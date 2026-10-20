"""
Abuse limits for the public deployment: per-client request rates, a daily cap
on stored detections, and a maximum upload size.

The per-client limiter is in memory, so it's per instance and resets when
Cloud Run scales to zero. That's enough to stop someone hammering the API
while they keep it warm (max instances = 2, so at worst 2x the limit). The
daily storage cap is the real cost guard (each stored detection is a Pinata
upload plus an on-chain transaction), so it's counted in Postgres: shared
across instances, durable across restarts, and not bypassable by switching IPs.
"""
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, UploadFile

from backend import db

WINDOW_SECONDS = 3600
LIMITS_PER_HOUR = {
    "upload": int(os.getenv("UPLOADS_PER_HOUR", "20")),
    "verify": int(os.getenv("VERIFIES_PER_HOUR", "60")),
}
MAX_STORED_DETECTIONS_PER_DAY = int(os.getenv("MAX_STORED_DETECTIONS_PER_DAY", "25"))
MAX_UPLOAD_BYTES = int(float(os.getenv("MAX_UPLOAD_MB", "10")) * 1024 * 1024)

# (action, client_ip) -> timestamps of recent requests
_hits: dict[tuple[str, str], deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """
    The caller's IP. Behind Cloud Run, request.client is Google's front end;
    the real client IP is the entry Google appends to X-Forwarded-For, i.e.
    the last one. Earlier entries are client-supplied and can be spoofed.
    Locally there's no X-Forwarded-For, so request.client is the caller.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def check_rate(request: Request, action: str) -> None:
    """Raises 429 if this client has used up its hourly allowance for `action`."""
    now = time.monotonic()
    hits = _hits[(action, client_ip(request))]
    while hits and now - hits[0] > WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= LIMITS_PER_HOUR[action]:
        retry_after = int(WINDOW_SECONDS - (now - hits[0])) + 1
        raise HTTPException(
            status_code=429,
            detail=f"Too many {action} requests; try again in {retry_after // 60 + 1} minutes.",
            headers={"Retry-After": str(retry_after)},
        )
    hits.append(now)
    _prune(now)


def _prune(now: float) -> None:
    """Drops clients with no hits in the window so memory doesn't grow forever."""
    if len(_hits) < 1000:
        return
    for key in [k for k, v in _hits.items() if not v or now - v[-1] > WINDOW_SECONDS]:
        del _hits[key]


def check_daily_storage_cap() -> None:
    """Raises 429 once the deployment has stored its daily quota of detections."""
    if db.detections_stored_in_last_day() >= MAX_STORED_DETECTIONS_PER_DAY:
        raise HTTPException(
            status_code=429,
            detail="This demo has reached its daily limit of stored detections; please try again tomorrow.",
        )


def check_upload_size(file: UploadFile) -> None:
    if file.size is not None and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large; the limit is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB. Short (5-10 s) clips work best.",
        )
