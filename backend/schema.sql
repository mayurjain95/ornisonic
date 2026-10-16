-- Applied on every backend startup (backend/db.py), so statements must stay
-- idempotent. Same schema locally (docker compose) and in production (Neon).

-- One row per stored watchlist match. id is the API's detection_id; it is
-- unrelated to onchain_detection_id (the contract's array index).
CREATE TABLE IF NOT EXISTS detections (
    id                   BIGSERIAL PRIMARY KEY,
    species              TEXT NOT NULL,
    scientific_name      TEXT NOT NULL,
    confidence           DOUBLE PRECISION NOT NULL,
    iucn_status          TEXT NOT NULL,
    start_time           DOUBLE PRECISION,
    end_time             DOUBLE PRECISION,
    ipfs_cid             TEXT NOT NULL,
    audio_hash           TEXT NOT NULL,  -- sha256 hex of the raw audio bytes
    onchain_tx_hash      TEXT,
    onchain_detection_id BIGINT,
    onchain_error        TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Every /upload call, matched or not; backs GET /stats.
CREATE TABLE IF NOT EXISTS uploads (
    id         BIGSERIAL PRIMARY KEY,
    filename   TEXT,
    matched    BOOLEAN NOT NULL,
    species    TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
