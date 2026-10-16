"""
FastAPI app: upload audio -> classify -> if endangered match, store on IPFS.

Endpoints:
  POST /upload         upload an audio clip for classification + storage
  GET  /detections      list of stored detections (Postgres, see backend/db.py)
  POST /verify/{id}     re-verify a detection by id against re-uploaded audio
                        (local sha256 hash, plus, if the detection was
                        anchored, the on-chain keccak256 hash and a
                        cross-check of the DB record against the chain)
  GET  /stats           total clips processed / watchlist matches
"""
import hashlib
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend import blockchain, classifier, db, ipfs_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    # Load BirdNET before the server accepts traffic, so the first upload
    # after a cold start doesn't also pay for model loading.
    classifier.get_analyzer()
    yield
    db.close_db()


app = FastAPI(title="Ornisonic", lifespan=lifespan)

# The deployed frontend (Firebase Hosting) calls the API cross-origin. Local
# dev doesn't need this: the Vite dev server proxies /api to the backend.
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "https://ornisonic.web.app,https://ornisonic.firebaseapp.com"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS if o.strip()],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def hash_audio(file_path: str) -> str:
    """Returns the sha256 hash of the raw audio file bytes, hex-encoded."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def check_onchain(record: dict, file_path: str) -> dict:
    """
    Compares the re-uploaded audio and the DB record against the anchored
    on-chain record, so a tampered DB row can't pass verification.
    """
    result = {
        "checked": False,
        "valid": None,               # audio keccak256 == on-chain hash
        "record_matches_db": None,   # DB fields == on-chain fields
        "mismatched_fields": [],
    }
    try:
        onchain_record = blockchain.get_detection(record["onchain_detection_id"])
        audio_hash = "0x" + blockchain.hash_audio(file_path).hex()
    except Exception as e:
        # RPC/config failure: the chain couldn't be asked, not a mismatch.
        result["error"] = str(e)
        return result

    result["checked"] = True
    if onchain_record is None:
        result["valid"] = False
        result["record_matches_db"] = False
        result["error"] = "No such detection on-chain"
        return result

    result["valid"] = onchain_record["audio_hash"] == audio_hash
    expected = {
        "ipfs_cid": record["ipfs_cid"],
        "species_name": record["scientific_name"],
        "confidence_bps": int(record["confidence"] * 10000),  # as sent in anchor_detection
    }
    result["mismatched_fields"] = [
        field for field, value in expected.items() if onchain_record[field] != value
    ]
    result["record_matches_db"] = not result["mismatched_fields"]
    return result


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = classifier.classify_audio(tmp_path)
        matches = result["matches"]

        if not matches:
            db.log_upload(file.filename, matched=False, species=[])
            return {
                "status": "no_endangered_species_detected",
                "matches": [],
                "best_guess": result["best_guess"],
            }

        db.log_upload(file.filename, matched=True, species=[m["scientific_name"] for m in matches])

        results = []
        for match in matches:
            cid = ipfs_client.upload_to_ipfs(tmp_path)
            audio_hash = hash_audio(tmp_path)

            record = {
                **match,
                "ipfs_cid": cid,
                "audio_hash": audio_hash,
            }

            try:
                anchor_result = blockchain.anchor_detection(
                    file_path=tmp_path, ipfs_cid=cid,
                    species_name=match["scientific_name"], confidence=match["confidence"],
                )
                record["onchain_tx_hash"] = anchor_result["tx_hash"]
                record["onchain_detection_id"] = anchor_result["detection_id"]
            except Exception as e:
                record["onchain_tx_hash"] = None
                record["onchain_error"] = str(e)

            results.append(db.insert_detection(record))

        return {"status": "stored", "matches": results}

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/detections")
async def list_detections():
    detections = db.list_detections()
    return {"count": len(detections), "detections": detections}


@app.get("/stats")
async def stats():
    return db.upload_stats()


@app.post("/verify/{detection_id}")
async def verify_detection(detection_id: int, file: UploadFile = File(...)):
    record = db.get_detection(detection_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such detection")

    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        local_valid = hash_audio(tmp_path) == record["audio_hash"]

        onchain = {"checked": False, "valid": None}
        if record["onchain_detection_id"] is not None:
            onchain = check_onchain(record, tmp_path)

        # The chain is the source of truth when it could be checked; the local
        # sha256 is the fallback for unanchored records or an unreachable RPC.
        if onchain["checked"]:
            verified = onchain["valid"] and onchain["record_matches_db"]
        else:
            verified = local_valid

        body = {
            "verified": verified,
            "detection_id": detection_id,
            "local_valid": local_valid,
            "onchain": onchain,
        }
        return JSONResponse(body, status_code=200 if verified else 409)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/")
async def root():
    return {"status": "ok", "service": "ornisonic"}
