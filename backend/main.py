"""
FastAPI app: upload audio -> classify -> if endangered match, store on IPFS.

Endpoints:
  POST /upload         upload an audio clip for classification + storage
  GET  /detections      list of stored detections (in-memory for MVP)
  POST /verify/{id}     re-verify a detection by id against re-uploaded audio
"""
import hashlib
import shutil
import tempfile
import time
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException

from backend import classifier, ipfs_client

app = FastAPI(title="Ornisonic")

# In-memory store for the MVP; swap for a real DB (Postgres/SQLite) once this works.
_detections_log: list[dict] = []
_next_id = 0


def hash_audio(file_path: str) -> str:
    """Returns the sha256 hash of the raw audio file bytes, hex-encoded."""
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


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
            return {
                "status": "no_endangered_species_detected",
                "matches": [],
                "best_guess": result["best_guess"],
            }

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

            _detections_log.append(record)
            results.append(record)

        return {"status": "stored", "matches": results}

    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/detections")
async def list_detections():
    return {"count": len(_detections_log), "detections": _detections_log}


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
        return {"verified": True, "detection_id": detection_id}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/")
async def root():
    return {"status": "ok", "service": "ornisonic"}
