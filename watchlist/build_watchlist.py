"""
Builds watchlist.json: the intersection of species BirdNET can already
detect and species with a threatened IUCN Red List status.

Requires IUCN_TOKEN in .env (v4 API token from https://api.iucnredlist.org).
"""
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

IUCN_TOKEN = os.getenv("IUCN_TOKEN")
IUCN_BASE = "https://api.iucnredlist.org/api/v4"
THREATENED_STATUSES = {"CR", "EN", "VU"}  # Critically Endangered, Endangered, Vulnerable

OUTPUT_PATH = Path(__file__).parent / "watchlist.json"


def get_birdnet_species_labels() -> list[str]:
    """
    Loads BirdNET's supported species labels via birdnetlib's bundled label file.
    Returns scientific names (BirdNET labels are "Scientific name_Common name").
    """
    from birdnetlib.analyzer import Analyzer

    analyzer = Analyzer()
    labels = analyzer.labels  # list of "Scientific_Common" strings
    scientific_names = [label.split("_")[0].strip() for label in labels]
    return scientific_names


def get_iucn_status(scientific_name: str) -> str | None:
    """Queries the IUCN Red List v4 API for a species' current conservation status."""
    if not IUCN_TOKEN:
        raise RuntimeError("Set IUCN_TOKEN in .env first")

    parts = scientific_name.split(" ", 1)
    if len(parts) != 2:
        return None
    genus_name, species_name = parts

    headers = {"Authorization": f"Bearer {IUCN_TOKEN}", "accept": "application/json"}
    params = {"genus_name": genus_name, "species_name": species_name}

    for attempt in range(3):
        resp = requests.get(
            f"{IUCN_BASE}/taxa/scientific_name", headers=headers, params=params, timeout=10
        )
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 5))
            time.sleep(wait)
            continue
        break

    if resp.status_code != 200:
        return None

    assessments = resp.json().get("assessments", [])
    latest = next((a for a in assessments if a.get("latest")), None)
    if latest is None:
        return None

    return latest.get("red_list_category_code")  # e.g. "EN", "VU", "LC"


def build_watchlist():
    print("Loading BirdNET species labels...")
    species = get_birdnet_species_labels()
    print(f"Found {len(species)} BirdNET-supported species. Checking IUCN status...")

    watchlist = []
    for i, name in enumerate(species):
        status = get_iucn_status(name)
        if status in THREATENED_STATUSES:
            watchlist.append({"scientific_name": name, "iucn_status": status})
            print(f"  [{status}] {name}")

        # Be polite to the API even though v4's rate limit isn't publicly documented
        time.sleep(0.2)

        if i % 100 == 0:
            print(f"  ...checked {i}/{len(species)}")

    OUTPUT_PATH.write_text(json.dumps(watchlist, indent=2))
    print(f"\nWrote {len(watchlist)} threatened species to {OUTPUT_PATH}")


if __name__ == "__main__":
    build_watchlist()
