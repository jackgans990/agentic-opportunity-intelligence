import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WATCHLIST_FILE = ROOT / "sources/raw/watchlist.csv"
PROJECTS_FILE = ROOT / "sources/raw/discovered_projects.csv"
OUTPUT_FILE = ROOT / "sources/raw/monitoring_events.csv"

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


def make_event_id(item):
    identity = "|".join([
        str(item.get("project_id", "")),
        str(item.get("event_type", "")),
        str(item.get("reason", "")),
        str(item.get("source", "")),
    ])
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]


def main():
    parser = argparse.ArgumentParser(
        description="Record new events affecting active watchlist projects."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="JSONL file containing newly detected events."
    )
    args = parser.parse_args()

    input_file = Path(args.input)

    if not input_file.exists():
        raise SystemExit("Monitoring input file not found.")

    watchlist = load_csv(WATCHLIST_FILE)
    projects = load_csv(PROJECTS_FILE)
    events = load_csv(OUTPUT_FILE)

    active_ids = {
        row.get("entity_id", "")
        for row in watchlist
        if row.get("entity_type") == "project"
        and row.get("status") == "active"
    }

    project_ids = {
        row.get("project_id", "")
        for row in projects
    }

    known_events = {
        row.get("event_id", "")
        for row in events
    }

    added = 0
    skipped = 0

    with input_file.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, 1):
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

            project_id = str(item.get("project_id", "")).strip()
            event_type = str(item.get("event_type", "")).strip()
            reason = str(item.get("reason", "")).strip()
            source = str(item.get("source", "")).strip()

            if (
                not project_id
                or not event_type
                or not reason
                or not source
                or project_id not in active_ids
                or project_id not in project_ids
            ):
                skipped += 1
                continue

            event_id = make_event_id(item)

            if event_id in known_events:
                skipped += 1
                continue

            events.append({
                "event_id": event_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entity_type": "project",
                "entity_id": project_id,
                "event_type": event_type,
                "reason": reason,
                "source": source,
                "reassessment_required": "true",
            })

            known_events.add(event_id)
            added += 1

    save_csv(OUTPUT_FILE, events)

    print("Monitoring completed.")
    print(f"New events: {added}")
    print(f"Skipped: {skipped}")
    print(f"Total events: {len(events)}")


if __name__ == "__main__":
    main()
