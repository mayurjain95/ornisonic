"""
Rebuilds `detections` rows from records already anchored on DetectionRegistry,
e.g. to populate a fresh database (local or Neon) with past detections.

For each on-chain record not yet in the DB, it downloads the audio from IPFS,
checks its keccak256 against the on-chain hash, and inserts a row with the
on-chain species, confidence, CID and timestamp. Common name and IUCN status
come from BirdNET's label file and watchlist.json. Detection times within the
clip and the anchoring tx hash aren't stored on-chain, so they're left NULL.

Safe to re-run: on-chain ids already in the DB are skipped. Read-only on the
chain (no gas). Run from the repo root:

    python -m scripts.backfill_from_chain
"""
import hashlib

import requests
from birdnetlib.analyzer import LABEL_PATH

from backend import blockchain, db
from backend.classifier import load_watchlist

IPFS_GATEWAYS = [
    "https://gateway.pinata.cloud/ipfs/",
    "https://ipfs.io/ipfs/",
]


def load_common_names() -> dict[str, str]:
    """Returns {scientific_name: common_name} from BirdNET's "Scientific_Common" labels."""
    names = {}
    with open(LABEL_PATH) as f:
        for line in f:
            scientific, _, common = line.strip().partition("_")
            names[scientific] = common
    return names


def fetch_from_ipfs(cid: str) -> bytes:
    errors = []
    for gateway in IPFS_GATEWAYS:
        try:
            resp = requests.get(gateway + cid, timeout=60)
            resp.raise_for_status()
            return resp.content
        except requests.RequestException as e:
            errors.append(f"{gateway}: {e}")
    raise RuntimeError(f"Could not fetch {cid} from IPFS: {errors}")


def confidence_from_bps(bps: int) -> float:
    """
    A float that maps back to exactly `bps` under int(confidence * 10000), the
    conversion anchor_detection and /verify's cross-check use.
    """
    confidence = bps / 10000
    while int(confidence * 10000) < bps:
        confidence += 1e-9
    return confidence


def main():
    db.init_db()
    _, contract, _ = blockchain.get_web3()
    total = contract.functions.totalDetections().call()
    existing = db.anchored_onchain_ids()
    common_names = load_common_names()
    watchlist = load_watchlist()
    audio_cache: dict[str, bytes] = {}

    inserted = skipped = failed = 0
    for onchain_id in range(total):
        if onchain_id in existing:
            skipped += 1
            continue

        record = blockchain.get_detection(onchain_id)
        cid = record["ipfs_cid"]
        try:
            if cid not in audio_cache:
                audio_cache[cid] = fetch_from_ipfs(cid)
        except RuntimeError as e:
            print(f"#{onchain_id}: {e}")
            failed += 1
            continue
        audio = audio_cache[cid]

        if "0x" + blockchain.Web3.keccak(audio).hex() != record["audio_hash"]:
            print(f"#{onchain_id}: IPFS audio for {cid} doesn't match the on-chain hash, skipping")
            failed += 1
            continue

        scientific_name = record["species_name"]
        row = db.insert_detection({
            "species": common_names.get(scientific_name, scientific_name),
            "scientific_name": scientific_name,
            "confidence": confidence_from_bps(record["confidence_bps"]),
            "iucn_status": watchlist.get(scientific_name, "unknown"),
            "ipfs_cid": cid,
            "audio_hash": hashlib.sha256(audio).hexdigest(),
            "onchain_detection_id": onchain_id,
            "created_at": record["timestamp"],
        })
        print(f"#{onchain_id}: inserted as detection {row['detection_id']} ({row['species']})")
        inserted += 1

    db.close_db()
    print(f"Done: {inserted} inserted, {skipped} already present, {failed} failed")


if __name__ == "__main__":
    main()
