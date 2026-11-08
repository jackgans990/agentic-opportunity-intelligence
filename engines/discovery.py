import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

OUTPUT_FILE = ROOT / "sources" / "raw" / "discovered_projects.csv"

FIELDS = [
    "project_id",
    "project_name",
    "website",
    "x_account",
    "discord_url",
    "chain",
    "category",
    "first_seen_at",
    "discovery_source",
    "discovery_query",
    "initial_status",
    "verification_status",
    "notes",
]


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def make_project_id(item):
    identity = "|".join([
        normalize(item.get("project_name")),
        normalize(item.get("chain")),
        normalize(item.get("website")),
    ])

    return re.sub(r"[^a-z0-9]+", "-", identity).strip("-")


def load_existing():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def process_item(item):
    now = datetime.now(timezone.utc).isoformat()

    project_name = str(item.get("project_name", "")).strip()

    if not project_name:
        return None

    project_id = str(item.get("project_id") or make_project_id(item))

    return {
        "project_id": project_id,
        "project_name": project_name,
        "website": item.get("website", ""),
        "x_account": item.get("x_account", ""),
        "discord_url": item.get("discord_url", ""),
        "chain": item.get("chain", ""),
        "category": item.get("category", ""),
        "first_seen_at": now,
        "discovery_source": item.get("discovery_source", "unknown"),
        "discovery_query": item.get("discovery_query", ""),
        "initial_status": "discovered",
        "verification_status": "unverified",
        "notes": item.get("notes", ""),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Process and deduplicate discovered project candidates."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSONL file containing discovery results."
    )

    args = parser.parse_args()
    input_file = Path(args.input)

    if not input_file.exists():
        raise SystemExit(f"Input file not found: {input_file}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = load_existing()
    known_ids = {
        normalize(row.get("project_id"))
        for row in existing
    }

    added = 0
    skipped = 0

    with input_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipped invalid JSON at line {line_number}")
                skipped += 1
                continue

            if not isinstance(item, dict):
                skipped += 1
                continue

            candidate = process_item(item)

            if candidate is None:
                skipped += 1
                continue

            project_id = normalize(candidate["project_id"])

            if project_id in known_ids:
                skipped += 1
                continue

            existing.append(candidate)
            known_ids.add(project_id)
            added += 1

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    print("Discovery processing completed.")
    print(f"New candidates: {added}")
    print(f"Skipped or duplicated: {skipped}")
    print(f"Total candidates: {len(existing)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
