import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = ROOT / "sources" / "raw" / "discovered_projects.csv"
OUTPUT_FILE = ROOT / "sources" / "raw" / "watchlist.csv"

FIELDS = [
    "watchlist_id",
    "entity_type",
    "entity_id",
    "status",
    "reason_added",
    "missing_evidence",
    "last_evaluated_at",
    "next_review_at",
    "added_at",
    "removal_reason",
]


def load_csv(path):
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    parser = argparse.ArgumentParser(
        description="Maintain active opportunity watchlist."
    )
    parser.add_argument(
        "--evaluations",
        required=True,
        help="Path to a CSV file containing evaluation results."
    )
    args = parser.parse_args()

    evaluation_file = Path(args.evaluations)

    if not INPUT_FILE.exists():
        raise SystemExit("Discovered projects file not found.")

    if not evaluation_file.exists():
        raise SystemExit("Evaluation file not found.")

    projects = load_csv(INPUT_FILE)
    evaluations = load_csv(evaluation_file)
    existing = load_csv(OUTPUT_FILE)

    existing_ids = {
        row.get("entity_id", "")
        for row in existing
        if row.get("status") != "removed"
    }

    latest_evaluations = {}

    for evaluation in evaluations:
        project_id = evaluation.get("project_id", "")
        if project_id:
            latest_evaluations[project_id] = evaluation

    added = 0

    for project in projects:
        project_id = project.get("project_id", "")

        if not project_id or project_id in existing_ids:
            continue

        evaluation = latest_evaluations.get(project_id)

        if evaluation:
            qualification = evaluation.get(
                "qualification_status", ""
            )

            if qualification not in {
                "active_watchlist",
                "insufficient_evidence",
                "provisional",
            }:
                continue

            reason = qualification
            missing = evaluation.get("unknown_dimensions", "")
            evaluated_at = evaluation.get("evaluated_at", "")
        else:
            reason = "not_yet_evaluated"
            missing = "evaluation_pending"
            evaluated_at = ""

        now = datetime.now(timezone.utc).isoformat()

        existing.append({
            "watchlist_id": f"project-{project_id}",
            "entity_type": "project",
            "entity_id": project_id,
            "status": "active",
            "reason_added": reason,
            "missing_evidence": missing,
            "last_evaluated_at": evaluated_at,
            "next_review_at": "",
            "added_at": now,
            "removal_reason": "",
        })

        existing_ids.add(project_id)
        added += 1

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    print("Watchlist update completed.")
    print(f"New entries: {added}")
    print(f"Active entries: {len(existing_ids)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
