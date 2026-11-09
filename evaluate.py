"""Compare the AI's ratings with my own."""
import csv
import json
import sys
from pathlib import Path

from store import list_items

RATINGS_PATH = Path("data/my_ratings.csv")


def load_my_ratings() -> dict:
    """My ratings, keyed by filename."""
    with open(RATINGS_PATH, newline="") as f:
        return {row["filename"]: row for row in csv.DictReader(f)}


def compare(label: str) -> dict:
    mine = load_my_ratings()
    rows = []
    for item in list_items():
        me = mine.get(item["filename"])
        if not me or not me["difficulty"] or item["difficulty"] is None:
            continue
        rows.append({
            "file": item["filename"],
            "my_diff": int(me["difficulty"]),
            "ai_diff": int(item["difficulty"]),
            "my_hours": float(me["est_hours"]),
            "ai_hours": float(item["est_hours"]),
        })

    if not rows:
        print("Nothing to compare: check my_ratings.csv and that items are scored.")
        return {}

    print(f"\n=== {label} ===")
    print(f"{'file':<38} {'me':>3} {'AI':>3}   {'me h':>5} {'AI h':>5}")
    for r in rows:
        print(f"{r['file'][:38]:<38} {r['my_diff']:>3} {r['ai_diff']:>3}   "
              f"{r['my_hours']:>5.1f} {r['ai_hours']:>5.1f}")

    n = len(rows)
    summary = {
        "label": label,
        "items": n,
        # average size of the difficulty gap (0 = perfect)
        "difficulty_mae": round(sum(abs(r["ai_diff"] - r["my_diff"]) for r in rows) / n, 2),
        # share of items where the AI is within 1 point of me
        "within_1": round(sum(abs(r["ai_diff"] - r["my_diff"]) <= 1 for r in rows) / n, 2),
        # average size of the hours gap
        "hours_mae": round(sum(abs(r["ai_hours"] - r["my_hours"]) for r in rows) / n, 2),
        # positive = AI overestimates hours on average
        "hours_bias": round(sum(r["ai_hours"] - r["my_hours"] for r in rows) / n, 2),
    }

    print(f"\nDifficulty: off by {summary['difficulty_mae']} on average, "
          f"within 1 point on {summary['within_1']:.0%} of items")
    print(f"Hours: off by {summary['hours_mae']}h on average "
          f"({'over' if summary['hours_bias'] > 0 else 'under'}estimates by "
          f"{abs(summary['hours_bias'])}h)")

    Path(f"data/eval_{label}.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    compare(sys.argv[1] if len(sys.argv) > 1 else "v1")