"""
Handles anchoring detection records to DetectionRegistry.sol on Polygon Amoy,
and verifying records already anchored.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from web3 import Web3

load_dotenv()

RPC_URL = os.getenv("POLYGON_RPC_URL")
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")
ABI_PATH = Path(__file__).parent / "contract_abi.json"

_w3 = None
_contract = None
_account = None


def get_web3():
    global _w3, _contract, _account
    if _w3 is None:
        if not RPC_URL or not PRIVATE_KEY or not CONTRACT_ADDRESS:
            raise RuntimeError(
                "Set POLYGON_RPC_URL, WALLET_PRIVATE_KEY, CONTRACT_ADDRESS in .env "
                "(deploy the contract first via scripts/deploy_contract.py)"
            )
        _w3 = Web3(Web3.HTTPProvider(RPC_URL))
        _account = _w3.eth.account.from_key(PRIVATE_KEY)
        abi = json.loads(ABI_PATH.read_text())
        _contract = _w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
    return _w3, _contract, _account


def hash_audio(file_path: str) -> bytes:
    w3 = Web3()
    with open(file_path, "rb") as f:
        data = f.read()
    return w3.keccak(data)


def anchor_detection(file_path: str, ipfs_cid: str, species_name: str, confidence: float) -> dict:
    w3, contract, account = get_web3()
    audio_hash = hash_audio(file_path)
    confidence_bps = int(confidence * 10000)

    tx = contract.functions.anchorDetection(
        audio_hash, ipfs_cid, species_name, confidence_bps
    ).build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gasPrice": w3.eth.gas_price,
    })
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    logs = contract.events.DetectionAnchored().process_receipt(receipt)
    detection_id = logs[0]["args"]["id"] if logs else None

    return {
        "tx_hash": "0x" + tx_hash.hex(),
        "detection_id": detection_id,
        "audio_hash": "0x" + audio_hash.hex(),
    }


def verify_detection(detection_id: int, file_path: str) -> bool:
    w3, contract, _ = get_web3()
    audio_hash = hash_audio(file_path)
    return contract.functions.verify(detection_id, audio_hash).call()


def get_detection(detection_id: int) -> dict:
    _, contract, _ = get_web3()
    d = contract.functions.getDetection(detection_id).call()
    return {
        "audio_hash": "0x" + d[0].hex(),
        "ipfs_cid": d[1],
        "species_name": d[2],
        "confidence_bps": d[3],
        "timestamp": d[4],
        "submitter": d[5],
    }
