"""
Uploads audio files to IPFS via Pinata's free tier.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

PINATA_API_KEY = os.getenv("PINATA_API_KEY")
PINATA_SECRET_KEY = os.getenv("PINATA_SECRET_KEY")
PINATA_UPLOAD_URL = "https://api.pinata.cloud/pinning/pinFileToIPFS"


def upload_to_ipfs(file_path: str) -> str:
    """Uploads a file to IPFS via Pinata and returns the CID."""
    if not PINATA_API_KEY or not PINATA_SECRET_KEY:
        raise RuntimeError("Set PINATA_API_KEY and PINATA_SECRET_KEY in .env first")

    headers = {
        "pinata_api_key": PINATA_API_KEY,
        "pinata_secret_api_key": PINATA_SECRET_KEY,
    }

    with open(file_path, "rb") as f:
        files = {"file": f}
        resp = requests.post(PINATA_UPLOAD_URL, files=files, headers=headers, timeout=30)

    resp.raise_for_status()
    return resp.json()["IpfsHash"]
