import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT / "sources" / "raw" / "discovered_evidence.csv"

FIELDS = [
    "evidence_id",
    "entity_id",
    "evidence_type",
    "claim",
    "source",
    "source_type",
    "evidence_status",
    "confidence",
    "observed_at",
    "raw_data_reference",
    "notes",
]

VALID_TYPES = {
    "official_announcement",
    "social_signal",
    "wallet_activity",
    "onchain_transaction",
    "market_activity",
    "security_finding",
    "other",
}

VALID_STATUSES = {
    "unverified",
    "partially_verified",
    "verified",
    "contradicted",
}


def load_existing():
    if not OUTPUT_FILE.exists():
        return []

    with OUTPUT_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def normalize(item):
    evidence_id = str(item.get("evidence_id", "")).strip()
    entity_id = str(item.get("entity_id", "")).strip()
    claim = str(item.get("claim", "")).strip()
    source = str(item.get("source", "")).strip()

    if not all([evidence_id, entity_id, claim, source]):
        return None

    evidence_type = item.get("evidence_type", "other")
    if evidence_type not in VALID_TYPES:
        evidence_type = "other"

    status = item.get("evidence_status", "unverified")
    if status not in VALID_STATUSES:
        status = "unverified"

    confidence = item.get("confidence", "")

    try:
        if confidence != "":
            confidence = float(confidence)
            if not 0 <= confidence <= 1:
                confidence = ""
    except (ValueError, TypeError):
        confidence = ""

    return {
        "evidence_id": evidence_id,
        "entity_id": entity_id,
        "evidence_type": evidence_type,
        "claim": claim,
        "source": source,
        "source_type": item.get("source_type", ""),
        "evidence_status": status,
        "confidence": confidence,
        "observed_at": item.get(
            "observed_at",
            datetime.now(timezone.utc).isoformat()
        ),
        "raw_data_reference": item.get("raw_data_reference", ""),
        "notes": item.get("notes", ""),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Process and store opportunity evidence."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSONL file containing evidence records."
    )
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        raise SystemExit(f"Input file not found: {input_file}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing = load_existing()
    known_ids = {
        row.get("evidence_id", "").strip()
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
                print(f"Invalid JSON at line {line_number}")
                skipped += 1
                continue

            if not isinstance(item, dict):
                skipped += 1
                continue

            record = normalize(item)

            if record is None or record["evidence_id"] in known_ids:
                skipped += 1
                continue

            existing.append(record)
            known_ids.add(record["evidence_id"])
            added += 1

    with OUTPUT_FILE.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    print("Evidence processing completed.")
    print(f"New evidence: {added}")
    print(f"Skipped or duplicated: {skipped}")
    print(f"Total evidence records: {len(existing)}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
