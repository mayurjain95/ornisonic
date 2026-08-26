"""
FastAPI app: upload audio -> classify -> if endangered match, store on IPFS.

Endpoints:
  POST /upload         upload an audio clip for classification + storage
  GET  /detections      list of stored detections (in-memory for MVP)
  POST /verify/{id}     re-verify a detection by id against re-uploaded audio
                        (local sha256 hash, plus the on-chain keccak256 hash
                        if the detection was anchored)
  GET  /stats           total clips processed / watchlist matches, durable
                        across restarts (backend/upload_log.jsonl)
"""
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException

from backend import blockchain, classifier, ipfs_client

app = FastAPI(title="Ornisonic")

# In-memory store for the MVP; swap for a real DB (Postgres/SQLite) once this works.
_detections_log: list[dict] = []
_next_id = 0

# Append-only log of every /upload call (matched or not) so the total count
# of clips processed survives server restarts, unlike _detections_log above.
UPLOAD_LOG_PATH = Path(__file__).parent / "upload_log.jsonl"


def hash_audio(file_path: str) -> str:
    """Returns the sha256 hash of the raw audio file bytes, hex-encoded."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def log_upload(filename: str, matched: bool, species: list[str]) -> None:
    with open(UPLOAD_LOG_PATH, "a") as f:
        f.write(json.dumps({
            "timestamp": int(time.time()),
            "filename": filename,
            "matched": matched,
            "species": species,
        }) + "\n")


@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    global _next_id

    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        result = classifier.classify_audio(tmp_path)
        matches = result["matches"]

        if not matches:
            log_upload(file.filename, matched=False, species=[])
            return {
                "status": "no_endangered_species_detected",
                "matches": [],
                "best_guess": result["best_guess"],
            }

        log_upload(file.filename, matched=True, species=[m["scientific_name"] for m in matches])

        results = []
        for match in matches:
            cid = ipfs_client.upload_to_ipfs(tmp_path)
            audio_hash = hash_audio(tmp_path)

            record = {
                **match,
                "detection_id": _next_id,
                "ipfs_cid": cid,
                "audio_hash": audio_hash,
                "timestamp": int(time.time()),
            }
            _next_id += 1

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

            _detections_log.append(record)
            results.append(record)

        return {"status": "stored", "matches": results}

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/detections")
async def list_detections():
    return {"count": len(_detections_log), "detections": _detections_log}


@app.get("/stats")
async def stats():
    total = 0
    matched = 0
    if UPLOAD_LOG_PATH.exists():
        with open(UPLOAD_LOG_PATH) as f:
            for line in f:
                total += 1
                if json.loads(line)["matched"]:
                    matched += 1
    return {"total_clips_processed": total, "watchlist_matches": matched}


@app.post("/verify/{detection_id}")
async def verify_detection(detection_id: int, file: UploadFile = File(...)):
    record = next((d for d in _detections_log if d["detection_id"] == detection_id), None)
    if record is None:
        raise HTTPException(status_code=404, detail="No such detection")

    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        is_valid = hash_audio(tmp_path) == record["audio_hash"]
        if not is_valid:
            raise HTTPException(status_code=409, detail="Audio does not match stored record")

        onchain = {"checked": False, "valid": None}
        onchain_detection_id = record.get("onchain_detection_id")
        if onchain_detection_id is not None:
            try:
                onchain["valid"] = blockchain.verify_detection(onchain_detection_id, tmp_path)
                onchain["checked"] = True
            except Exception as e:
                onchain["error"] = str(e)

        return {"verified": True, "detection_id": detection_id, "onchain": onchain}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/")
async def root():
    return {"status": "ok", "service": "ornisonic"}
