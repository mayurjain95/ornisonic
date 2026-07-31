"""
Wraps birdnetlib to classify an audio file and return detections.
"""
import json
from pathlib import Path

from birdnetlib import Recording
from birdnetlib.analyzer import Analyzer

WATCHLIST_PATH = Path(__file__).parent.parent / "watchlist" / "watchlist.json"

# BirdNET's 11 non-event classes (engine noise, human speech, etc.) — never
# real species, so they're excluded from the "closest match" fallback.
NON_SPECIES_LABELS = {
    "Dog",
    "Engine",
    "Environmental",
    "Fireworks",
    "Gun",
    "Human non-vocal",
    "Human vocal",
    "Human whistle",
    "Noise",
    "Power tools",
    "Siren",
}

_analyzer = None


def get_analyzer() -> Analyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = Analyzer()
    return _analyzer


def load_watchlist() -> dict[str, str]:
    """Returns {scientific_name: iucn_status} for quick lookup."""
    if not WATCHLIST_PATH.exists():
        return {}
    entries = json.loads(WATCHLIST_PATH.read_text())
    return {e["scientific_name"]: e["iucn_status"] for e in entries}


def classify_audio(file_path: str, min_confidence: float = 0.5) -> dict:
    """
    Runs BirdNET on the given audio file.

    Returns {"matches": [...], "best_guess": {...} | None}
      - matches: detections that hit a species on the endangered watchlist.
      - best_guess: BirdNET's single highest-confidence real-bird detection
        that ISN'T on the watchlist, for when there's no match — lets the UI
        say what it thinks it heard instead of just "nothing found".
    """
    watchlist = load_watchlist()
    analyzer = get_analyzer()

    recording = Recording(analyzer, file_path, min_conf=min_confidence)
    recording.analyze()

    matches = []
    best_guess = None
    for detection in recording.detections:
        scientific_name = detection["scientific_name"]
        if scientific_name in watchlist:
            matches.append({
                "species": detection["common_name"],
                "scientific_name": scientific_name,
                "confidence": detection["confidence"],
                "iucn_status": watchlist[scientific_name],
                "start_time": detection["start_time"],
                "end_time": detection["end_time"],
            })
        elif scientific_name not in NON_SPECIES_LABELS:
            if best_guess is None or detection["confidence"] > best_guess["confidence"]:
                best_guess = {
                    "species": detection["common_name"],
                    "scientific_name": scientific_name,
                    "confidence": detection["confidence"],
                }

    return {"matches": matches, "best_guess": best_guess}
