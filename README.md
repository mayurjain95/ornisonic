# Ornisonic

Live endangered-species audio detection, hashed and stored on IPFS, and anchored on-chain (Polygon Amoy testnet) for independently verifiable, tamper-proof records.

## Screenshots

**Watchlist match** — a Black Rail call gets classified, hashed, and pinned to IPFS:

![Detection card showing a Black Rail match with confidence, audio hash, and IPFS link](docs/screenshots/detection-match.png)

**No match** — nothing on the watchlist, so the UI shows BirdNET's closest real-bird guess instead of storing anything:

![No watchlist match message with a closest-predicted-species guess](docs/screenshots/no-match.png)

## Architecture

```
Audio upload
   -> BirdNET classification (backend/classifier.py)
   -> Filter against endangered watchlist (watchlist/watchlist.json)
   -> On match:
        -> Upload audio to IPFS via Pinata (backend/ipfs_client.py)
        -> Hash audio, anchor record on-chain (backend/blockchain.py)
   -> Detection stored + queryable via FastAPI (backend/main.py)
   -> Anyone can re-hash the original audio and verify it against both the
      local record and the on-chain record (amoy.polygonscan.com)
```

The blockchain layer is optional and fails soft: if anchoring errors (no
funds, RPC down), the upload still succeeds and stores the IPFS/local record —
`onchain_error` is set on the response instead of a 500.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Get free API keys / accounts (all free tier)
- **Pinata** (IPFS storage): https://pinata.cloud -> API key + secret
- **IUCN Red List API** (species conservation status): https://apiv3.iucnredlist.org/api/v3/token -> free token

### 3. Set environment variables
Copy `.env.example` to `.env` and fill in:
```
PINATA_API_KEY=...
PINATA_SECRET_KEY=...
IUCN_TOKEN=...
```
`.env` is gitignored — never put real secrets in `.env.example` (that file is
committed as a template and should stay blank).

### 4. Build the watchlist
```bash
python watchlist/build_watchlist.py
```
This cross-references IUCN Red List status against BirdNET's supported species and writes `watchlist/watchlist.json`.

### 5. (Optional) Set up on-chain anchoring
Skip this if you just want IPFS/local hashing — the app works fully without it.

1. **Get a Polygon Amoy RPC URL.** Any public/free RPC endpoint works (e.g. a
   [dRPC](https://drpc.org) or [Alchemy](https://alchemy.com) Amoy endpoint).
2. **Create a wallet** and fund it with free testnet POL from an
   [Amoy faucet](https://faucet.polygon.technology/) — no real value, this
   never touches mainnet. A few faucets gate behind a mainnet-activity check;
   if you hit that, fund the wallet with a small amount of real ETH first to
   pass the check.
3. Add to `.env`:
   ```
   POLYGON_RPC_URL=...
   WALLET_PRIVATE_KEY=...
   ```
4. **Deploy the contract:**
   ```bash
   python scripts/deploy_contract.py
   ```
   This compiles `contracts/DetectionRegistry.sol`, prints the estimated gas
   cost before sending (so you can confirm it fits your balance), deploys to
   Amoy, and writes `backend/contract_abi.json`. Copy the printed address into
   `.env` as `CONTRACT_ADDRESS=...`.
5. Restart the backend. `/upload` will now anchor watchlist matches on-chain,
   and `/verify/{id}` will check the on-chain hash alongside the local one.

To make transactions to the contract decode as readable function calls
instead of raw calldata on the explorer, verify it (one-time, free, via the
["Verify Contract" flow](https://amoy.polygonscan.com/verifyContract) —
Solidity single file, matching compiler version, optimization off, MIT
license, no constructor arguments).

### 6. Run the backend
```bash
uvicorn backend.main:app --reload
```

### 7. Test it
```bash
curl -X POST "http://localhost:8000/upload" -F "file=@sample.wav"
```

### 8. Run the frontend
With the backend running on port 8000:
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 — the dev server proxies `/api/*` requests to the FastAPI backend, so no CORS setup is needed. Uploading a clip stores any endangered-species match and shows it as a card with its confidence, IPFS link, hash, and a verify button. If nothing on the watchlist matches, the UI instead shows BirdNET's closest real-bird prediction (with a thumbnail and a link to check its IUCN status) — nothing is stored in that case, since only watchlist matches get hashed and pinned to IPFS.

## Project layout
```
ornisonic/
├── watchlist/
│   └── build_watchlist.py     # IUCN + BirdNET overlap -> watchlist.json
├── contracts/
│   └── DetectionRegistry.sol  # on-chain detection registry
├── scripts/
│   └── deploy_contract.py     # one-time contract deploy to Amoy
├── backend/
│   ├── main.py                # FastAPI app: /upload, /detections, /verify
│   ├── classifier.py          # BirdNET wrapper
│   ├── ipfs_client.py         # Pinata upload
│   ├── blockchain.py          # web3.py client: anchor/verify on-chain
│   └── contract_abi.json      # generated by deploy_contract.py
├── frontend/                  # React (Vite) dashboard
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── components/
│   └── package.json
├── requirements.txt
└── .env.example
```

## Notes
- Start with short (5-10s) test clips; BirdNET works best on that length.
- `classify_audio` filters BirdNET detections at `min_confidence=0.5` (`backend/classifier.py`). This is lower than BirdNET's usual 0.7 default because secretive, endangered species (e.g. Black Rail) tend to score lower than common, loud ones even on a real call — a stricter threshold was filtering out genuine detections of the exact species this app is meant to catch.
- Polygon Amoy testnet transactions are free (faucet-funded test POL, no real value); real Polygon mainnet costs are also low (roughly $0.01–0.02/tx as of mid-2026) if this ever moves to production.
