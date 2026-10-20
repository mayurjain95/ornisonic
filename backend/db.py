"""
Postgres persistence for detections and the upload log.

The same code and schema (backend/schema.sql) run locally against the
docker-compose Postgres and in production against Neon; only DATABASE_URL
differs. With DATABASE_URL unset, it falls back to the local compose database.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv()

LOCAL_DATABASE_URL = "postgresql://ornisonic:ornisonic@localhost:5432/ornisonic"
DATABASE_URL = os.getenv("DATABASE_URL") or LOCAL_DATABASE_URL
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Columns returned to API clients, shaped like the old in-memory records.
DETECTION_COLUMNS = """
    id AS detection_id, species, scientific_name, confidence, iucn_status,
    start_time, end_time, ipfs_cid, audio_hash,
    onchain_tx_hash, onchain_detection_id, onchain_error,
    EXTRACT(EPOCH FROM created_at)::bigint AS timestamp
"""

_pool: ConnectionPool | None = None


def init_db() -> None:
    """Opens the connection pool and applies the schema."""
    global _pool
    _pool = ConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=5,
        # prepare_threshold=None: no server-side prepared statements, which
        # keeps this safe behind Neon's PgBouncer pooler.
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
        # Neon suspends idle computes and drops their connections; check each
        # connection before handing it out instead of failing the request.
        check=ConnectionPool.check_connection,
        open=True,
    )
    with _pool.connection() as conn:
        conn.execute(SCHEMA_PATH.read_text())


def close_db() -> None:
    if _pool is not None:
        _pool.close()


def _get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Database not initialised; call db.init_db() first")
    return _pool


def insert_detection(record: dict) -> dict:
    """
    Stores a detection and returns it with detection_id and timestamp set.
    created_at (unix seconds) is optional and defaults to now.
    """
    with _get_pool().connection() as conn:
        return conn.execute(
            f"""
            INSERT INTO detections (
                species, scientific_name, confidence, iucn_status,
                start_time, end_time, ipfs_cid, audio_hash,
                onchain_tx_hash, onchain_detection_id, onchain_error, created_at
            ) VALUES (
                %(species)s, %(scientific_name)s, %(confidence)s, %(iucn_status)s,
                %(start_time)s, %(end_time)s, %(ipfs_cid)s, %(audio_hash)s,
                %(onchain_tx_hash)s, %(onchain_detection_id)s, %(onchain_error)s,
                COALESCE(to_timestamp(%(created_at)s), now())
            )
            RETURNING {DETECTION_COLUMNS}
            """,
            {
                "start_time": None,
                "end_time": None,
                "onchain_tx_hash": None,
                "onchain_detection_id": None,
                "onchain_error": None,
                "created_at": None,
                **record,
            },
        ).fetchone()


def list_detections() -> list[dict]:
    with _get_pool().connection() as conn:
        return conn.execute(
            f"SELECT {DETECTION_COLUMNS} FROM detections ORDER BY created_at DESC, id DESC"
        ).fetchall()


def get_detection(detection_id: int) -> dict | None:
    with _get_pool().connection() as conn:
        return conn.execute(
            f"SELECT {DETECTION_COLUMNS} FROM detections WHERE id = %s",
            (detection_id,),
        ).fetchone()


def detections_stored_in_last_day() -> int:
    with _get_pool().connection() as conn:
        return conn.execute(
            "SELECT count(*) AS n FROM detections WHERE created_at > now() - interval '24 hours'"
        ).fetchone()["n"]


def anchored_onchain_ids() -> set[int]:
    with _get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT onchain_detection_id FROM detections WHERE onchain_detection_id IS NOT NULL"
        ).fetchall()
    return {r["onchain_detection_id"] for r in rows}


def log_upload(filename: str, matched: bool, species: list[str]) -> None:
    with _get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO uploads (filename, matched, species) VALUES (%s, %s, %s::text[])",
            (filename, matched, species),
        )


def upload_stats() -> dict:
    with _get_pool().connection() as conn:
        return conn.execute(
            """
            SELECT count(*) AS total_clips_processed,
                   count(*) FILTER (WHERE matched) AS watchlist_matches
            FROM uploads
            """
        ).fetchone()
