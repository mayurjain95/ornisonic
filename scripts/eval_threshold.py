"""
Compares BirdNET's watchlist-match behavior at min_confidence=0.5 (this app's
setting) vs 0.7 (BirdNET's default), on a small labeled set: true positives
(known watchlist species clips) and true negatives (common, non-watchlist
species clips). Reports false-positive rate and recall at each threshold.

This is a small sample (n=11) sourced from what's on hand locally plus a
handful of CC-licensed clips pulled from Wikimedia Commons — enough to show
the direction and magnitude of the tradeoff, not a statistically rigorous
benchmark. Treat the numbers as indicative, not final.
"""
import glob
import json
from pathlib import Path

from backend import classifier

ROOT = Path(__file__).parent.parent

# (file_path, true_scientific_name_or_None)
POSITIVES = [
    (str(p), "Laterallus jamaicensis")
    for p in (ROOT / "samples").glob("*Black Rail*")
]

NEGATIVE_DIRS = [ROOT / "samples", ROOT / "eval_data" / "negatives"]
NEGATIVE_EXCLUDE_SUBSTR = "Black Rail"

NEGATIVES = []
for d in NEGATIVE_DIRS:
    for ext in ("*.wav", "*.mp3", "*.ogg"):
        for p in d.glob(ext):
            if NEGATIVE_EXCLUDE_SUBSTR in p.name:
                continue
            NEGATIVES.append((str(p), None))

TEST_SET = POSITIVES + NEGATIVES


def run_at_threshold(threshold: float) -> dict:
    tp = fp = fn = tn = 0
    detail = []
    for file_path, true_species in TEST_SET:
        result = classifier.classify_audio(file_path, min_confidence=threshold)
        matched_species = {m["scientific_name"] for m in result["matches"]}
        is_match = len(matched_species) > 0

        if true_species is not None:
            if true_species in matched_species:
                tp += 1
                outcome = "TP"
            else:
                fn += 1
                outcome = "FN"
        else:
            if is_match:
                fp += 1
                outcome = "FP"
            else:
                tn += 1
                outcome = "TN"

        detail.append({
            "file": Path(file_path).name,
            "true_species": true_species,
            "matched": sorted(matched_species),
            "outcome": outcome,
        })

    n_pos = tp + fn
    n_neg = fp + tn
    return {
        "threshold": threshold,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "n_positives": n_pos, "n_negatives": n_neg,
        "recall": tp / n_pos if n_pos else None,
        "false_positive_rate": fp / n_neg if n_neg else None,
        "detail": detail,
    }


if __name__ == "__main__":
    print(f"Positives: {len(POSITIVES)}  Negatives: {len(NEGATIVES)}\n")

    results = [run_at_threshold(t) for t in (0.5, 0.7)]

    for r in results:
        print(f"--- threshold={r['threshold']} ---")
        print(f"  TP={r['tp']} FN={r['fn']}  (recall={r['recall']})")
        print(f"  FP={r['fp']} TN={r['tn']}  (false_positive_rate={r['false_positive_rate']})")
        for d in r["detail"]:
            print(f"    [{d['outcome']}] {d['file']}  true={d['true_species']}  matched={d['matched']}")
        print()

    out_path = Path(__file__).parent.parent / "eval_data" / "threshold_eval_results.json"
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Full results written to {out_path}")
