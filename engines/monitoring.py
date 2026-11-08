import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WATCHLIST_FILE = ROOT / "sources" / "raw" / "watchlist.csv"
PROJECTS_FILE = ROOT / "sources" / "raw" / "discovered_projects.csv"
OUTPUT_FILE = ROOT / "sources" / "raw" / "monitoring_events.csv"

FIELDS = [
    "event_id",
    "timestamp",
    "entity_type",
    "entity_id",
    "event_type",
    "reason",
    "source",
    "reassessment_required",
]


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
    parser = argparse.ArgumentParser(
        description="Identify watchlist candidates requiring reassessment."
    )
    parser.add_argument(
        "--event",
        default="scheduled_review",
        help="Event type that triggered this monitoring run."
    )
    parser.add_argument(
        "--entity-id",
        default="",
        help="Optional project ID to monitor."
    )
    args = parser.parse_args()

    watchlist = load_csv(WATCHLIST_FILE)
    projects = load_csv(PROJECTS_FILE)
    events = load_csv(OUTPUT_FILE)

    project_ids = {
        row.get("project_id", "")
        for row in projects
    }

    timestamp = datetime.now(timezone.utc).isoformat()
    added = 0

    for entry in watchlist:
        if entry.get("status") != "active":
            continue

        entity_id = entry.get("entity_id", "")

        if args.entity_id and entity_id != args.entity_id:
            continue

        if entry.get("entity_type") != "project":
            continue

        if entity_id not in project_ids:
            continue

        event_id = (
            f"{entity_id}-"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        )

        events.append({
            "event_id": event_id,
            "timestamp": timestamp,
            "entity_type": "project",
            "entity_id": entity_id,
            "event_type": args.event,
            "reason": "Active watchlist candidate requires reassessment.",
            "source": "internal_monitoring",
            "reassessment_required": "true",
        })

        added += 1

    save_csv(OUTPUT_FILE, events)

    print("Monitoring run completed.")
    print(f"Watchlist entries checked: {len(watchlist)}")
    print(f"Reassessment events created: {added}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
