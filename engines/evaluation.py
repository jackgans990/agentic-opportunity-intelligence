import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "scoring.yaml"
OUTPUT_FILE = ROOT / "sources" / "raw" / "evaluations.csv"

DIMENSIONS = {
    "market_demand": 20,
    "narrative_attention": 15,
    "audience_distribution": 15,
    "wallet_intelligence": 10,
    "timing_and_access": 15,
    "exit_and_liquidity": 15,
    "acquisition_economics": 5,
    "project_credibility": 5,
}

FIELDS = [
    "evaluation_id",
    "project_id",
    "evaluated_at",
    "opportunity_type",
    "opportunity_score",
    "evidence_coverage",
    "qualification_status",
    "assessable_weight",
    "unknown_dimensions",
    "dimension_scores",
]


def load_existing():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def evaluate(item):
    project_id = str(item.get("project_id", "")).strip()

    if not project_id:
        return None

    ratings = item.get("ratings", {})
    if not isinstance(ratings, dict):
        return None

    earned_points = 0
    assessable_weight = 0
    unknown_dimensions = []
    normalized_scores = {}

    for dimension, weight in DIMENSIONS.items():
        rating = ratings.get(dimension)

        if rating is None:
            unknown_dimensions.append(dimension)
            normalized_scores[dimension] = None
            continue

        try:
            rating = float(rating)
        except (ValueError, TypeError):
            unknown_dimensions.append(dimension)
            normalized_scores[dimension] = None
            continue

        if not 0 <= rating <= 5:
            unknown_dimensions.append(dimension)
            normalized_scores[dimension] = None
            continue

        earned_points += (rating / 5) * weight
        assessable_weight += weight
        normalized_scores[dimension] = rating

    if assessable_weight == 0:
        return None

    score = round(
        earned_points / assessable_weight * 100, 2
    )

    coverage = round(assessable_weight / 100, 2)

    opportunity_type = item.get(
        "opportunity_type", "free_mint"
    )

    threshold = {
        "free_mint": 70,
        "paid_mint": 90,
    }.get(opportunity_type)

    if threshold is None:
        qualification = "provisional"
    elif coverage < 0.60:
        qualification = "insufficient_evidence"
    elif score >= threshold:
        qualification = "qualified"
    else:
        qualification = "active_watchlist"

    return {
        "evaluation_id": str(
            item.get("evaluation_id") or
            f"{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        ),
        "project_id": project_id,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "opportunity_type": opportunity_type,
        "opportunity_score": score,
        "evidence_coverage": coverage,
        "qualification_status": qualification,
        "assessable_weight": assessable_weight,
        "unknown_dimensions": ";".join(unknown_dimensions),
        "dimension_scores": json.dumps(
            normalized_scores, ensure_ascii=False
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Calculate evidence-based opportunity scores."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSONL file containing project ratings."
    )

    args = parser.parse_args()
    input_file = Path(args.input)

    if not input_file.exists():
        raise SystemExit(f"Input file not found: {input_file}")

    if not CONFIG_FILE.exists():
        raise SystemExit("Scoring configuration not found.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = load_existing()
    known_ids = {
        row.get("evaluation_id", "") for row in existing
    }

    added = 0
    skipped = 0

    with input_file.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            if not isinstance(item, dict):
                skipped += 1
                continue

            record = evaluate(item)

            if record is None:
                skipped += 1
                continue

            if record["evaluation_id"] in known_ids:
                skipped += 1
                continue

            existing.append(record)
            known_ids.add(record["evaluation_id"])
            added += 1

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    print("Evaluation completed.")
    print(f"New evaluations: {added}")
    print(f"Skipped: {skipped}")
    print(f"Total evaluations: {len(existing)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
