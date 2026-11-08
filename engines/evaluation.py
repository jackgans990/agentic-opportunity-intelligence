import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "config" / "scoring.yaml"
OUTPUT_FILE = ROOT / "sources" / "raw" / "evaluations.csv"

FIELDS = [
    "evaluation_id", "project_id", "evaluated_at",
    "opportunity_type", "opportunity_score",
    "evidence_coverage", "qualification_status",
    "assessable_weight", "unknown_dimensions",
    "dimension_scores",
]


def load_config():
    try:
        import yaml
    except ImportError:
        raise SystemExit("Install PyYAML before running evaluation.")

    with CONFIG_FILE.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    scoring = config["scoring"]
    dimensions = {
        name: int(data["weight"])
        for name, data in scoring["dimensions"].items()
    }

    if sum(dimensions.values()) != 100:
        raise SystemExit("Scoring dimension weights must total 100.")

    return config, dimensions


def load_existing():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def evaluate(item, config, dimensions):
    project_id = str(item.get("project_id", "")).strip()
    ratings = item.get("ratings", {})

    if not project_id or not isinstance(ratings, dict):
        return None

    earned = 0
    assessable = 0
    unknown = []
    normalized = {}

    for dimension, weight in dimensions.items():
        rating = ratings.get(dimension)

        try:
            rating = float(rating)
            if not 0 <= rating <= 5:
                raise ValueError
        except (ValueError, TypeError):
            unknown.append(dimension)
            normalized[dimension] = None
            continue

        earned += (rating / 5) * weight
        assessable += weight
        normalized[dimension] = rating

    if assessable == 0:
        return None

    score = round(earned / assessable * 100, 2)
    coverage = round(assessable / 100, 2)

    opportunity_type = item.get("opportunity_type", "free_mint")
    qualification_config = config.get("qualification", {}).get(
        opportunity_type, {}
    )

    minimum_score = qualification_config.get("minimum_score")

    minimum_coverage = qualification_config.get(
        "minimum_evidence_coverage",
        config["scoring"]["evidence_coverage"].get(
            "minimum_for_qualification", 0.60
        ),
    )

    if minimum_score is None:
        qualification = "provisional"
    elif coverage < minimum_coverage:
        qualification = "provisional"
    elif score >= minimum_score:
        qualification = "qualified"
    else:
        qualification = "active_watchlist"

    now = datetime.now(timezone.utc).isoformat()

    return {
        "evaluation_id": item.get("evaluation_id") or
            f"{project_id}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
        "project_id": project_id,
        "evaluated_at": now,
        "opportunity_type": opportunity_type,
        "opportunity_score": score,
        "evidence_coverage": coverage,
        "qualification_status": qualification,
        "assessable_weight": assessable,
        "unknown_dimensions": ";".join(unknown),
        "dimension_scores": json.dumps(normalized, ensure_ascii=False),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Calculate evidence-based opportunity scores."
    )
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    input_file = Path(args.input)

    if not input_file.exists():
        raise SystemExit("Input file not found.")

    if not CONFIG_FILE.exists():
        raise SystemExit("Scoring configuration not found.")

    config, dimensions = load_config()
    existing = load_existing()

    known_ids = {row.get("evaluation_id", "") for row in existing}
    added = 0
    skipped = 0

    with input_file.open("r", encoding="utf-8-sig") as file:
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

            record = evaluate(item, config, dimensions)

            if record is None or record["evaluation_id"] in known_ids:
                skipped += 1
                continue

            existing.append(record)
            known_ids.add(record["evaluation_id"])
            added += 1

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    print("Evaluation completed.")
    print(f"New evaluations: {added}")
    print(f"Skipped: {skipped}")
    print(f"Total evaluations: {len(existing)}")


if __name__ == "__main__":
    main()
