"""
Compiles and deploys DetectionRegistry.sol to Polygon Amoy testnet.
Run once, then put the printed contract address into .env as CONTRACT_ADDRESS.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from solcx import compile_source, install_solc, set_solc_version
from web3 import Web3

load_dotenv()

CONTRACT_PATH = Path(__file__).parent.parent / "contracts" / "DetectionRegistry.sol"
RPC_URL = os.getenv("POLYGON_RPC_URL")
PRIVATE_KEY = os.getenv("WALLET_PRIVATE_KEY")
SOLC_VERSION = "0.8.24"


def compile_contract():
    install_solc(SOLC_VERSION)
    set_solc_version(SOLC_VERSION)
    source = CONTRACT_PATH.read_text()
    compiled = compile_source(source, output_values=["abi", "bin"], solc_version=SOLC_VERSION)
    _, contract_interface = compiled.popitem()
    return contract_interface["abi"], contract_interface["bin"]


def deploy():
    if not RPC_URL or not PRIVATE_KEY:
        raise RuntimeError("Set POLYGON_RPC_URL and WALLET_PRIVATE_KEY in .env first")

    print("Compiling contract...")
    abi, bytecode = compile_contract()

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = w3.eth.account.from_key(PRIVATE_KEY)
    print(f"Deploying from wallet: {account.address}")

    balance = w3.eth.get_balance(account.address)
    print(f"Wallet balance: {w3.from_wei(balance, 'ether')} POL (testnet)")
    if balance == 0:
        print("WARNING: wallet has 0 balance. Fund it from a Polygon Amoy faucet first.")

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = Contract.constructor().build_transaction({
        "from": account.address,
        "nonce": w3.eth.get_transaction_count(account.address),
        "gasPrice": w3.eth.gas_price,
    })
    tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)

    cost = tx["gas"] * tx["gasPrice"]
    if cost > balance:
        raise RuntimeError(
            f"Estimated deploy cost {w3.from_wei(cost, 'ether')} POL exceeds wallet balance "
            f"{w3.from_wei(balance, 'ether')} POL. Fund the wallet from an Amoy faucet."
        )
    print(f"Estimated gas: {tx['gas']} @ {w3.from_wei(tx['gasPrice'], 'gwei')} gwei "
          f"(~{w3.from_wei(cost, 'ether')} POL)")

    signed = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Deploy tx sent: {tx_hash.hex()}. Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"\nContract deployed at: {receipt.contractAddress}")

    abi_path = Path(__file__).parent.parent / "backend" / "contract_abi.json"
    abi_path.write_text(json.dumps(abi, indent=2))
    print(f"ABI saved to {abi_path}")
    print(f"\nAdd this to your .env:\nCONTRACT_ADDRESS={receipt.contractAddress}")


if __name__ == "__main__":
    deploy()
