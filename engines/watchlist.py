import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT_FILE = ROOT / "sources/raw/discovered_projects.csv"
OUTPUT_FILE = ROOT / "sources/raw/watchlist.csv"

FIELDS = [
    "watchlist_id", "entity_type", "entity_id", "status",
    "reason_added", "missing_evidence", "last_evaluated_at",
    "next_review_at", "added_at", "removal_reason",
]

WATCH_STATUSES = {
    "active_watchlist", "provisional", "insufficient_evidence",
    "not_yet_evaluated",
}


def load_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def save_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evaluations", required=True)
    args = parser.parse_args()

    evaluation_file = Path(args.evaluations)
    if not PROJECT_FILE.exists() or not evaluation_file.exists():
        raise SystemExit("Project or evaluation file not found.")

    projects = load_csv(PROJECT_FILE)
    evaluations = load_csv(evaluation_file)
    existing = load_csv(OUTPUT_FILE)

    latest = {}
    for evaluation in evaluations:
        project_id = evaluation.get("project_id", "")
        if not project_id:
            continue
        previous = latest.get(project_id)
        if previous is None or evaluation.get("evaluated_at", "") >= previous.get("evaluated_at", ""):
            latest[project_id] = evaluation

    entries = {
        row.get("entity_id"): row
        for row in existing
        if row.get("entity_type") == "project"
        and row.get("status") != "removed"
    }

    now = datetime.now(timezone.utc).isoformat()
    added = 0
    updated = 0

    for project in projects:
        project_id = project.get("project_id", "")
        if not project_id:
            continue

        evaluation = latest.get(project_id)
        qualification = (
            evaluation.get("qualification_status", "")
            if evaluation else "not_yet_evaluated"
        )

        if qualification == "qualified":
            continue

        if qualification not in WATCH_STATUSES:
            continue

        missing = (
            evaluation.get("unknown_dimensions", "")
            if evaluation else "evaluation_pending"
        )
        evaluated_at = (
            evaluation.get("evaluated_at", "")
            if evaluation else ""
        )

        if project_id in entries:
            entry = entries[project_id]
            entry["reason_added"] = qualification
            entry["missing_evidence"] = missing
            entry["last_evaluated_at"] = evaluated_at
            updated += 1
        else:
            entry = {
                "watchlist_id": f"project-{project_id}",
                "entity_type": "project",
                "entity_id": project_id,
                "status": "active",
                "reason_added": qualification,
                "missing_evidence": missing,
                "last_evaluated_at": evaluated_at,
                "next_review_at": "",
                "added_at": now,
                "removal_reason": "",
            }
            existing.append(entry)
            entries[project_id] = entry
            added += 1

    save_csv(OUTPUT_FILE, existing)

    print("Watchlist update completed.")
    print(f"New entries: {added}")
    print(f"Updated entries: {updated}")
    print(f"Active entries: {sum(1 for r in existing if r.get('status') == 'active')}")


if __name__ == "__main__":
    main()
