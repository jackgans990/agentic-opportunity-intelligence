
import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PROJECT_FILE = ROOT / "sources/raw/discovered_projects.csv"
EVIDENCE_FILE = ROOT / "sources/raw/discovered_evidence.csv"

PROJECT_FIELDS = [
    "project_id", "project_name", "website", "x_account",
    "discord_url", "chain", "category", "first_seen_at",
    "discovery_source", "discovery_query", "initial_status",
    "verification_status", "notes"
]

EVIDENCE_FIELDS = [
    "evidence_id", "entity_id", "evidence_type", "claim",
    "source", "source_type", "evidence_status", "confidence",
    "observed_at", "raw_data_reference", "notes"
]

VALID_EVIDENCE_TYPES = {
    "official_announcement", "social_signal", "wallet_activity",
    "onchain_transaction", "market_activity", "security_finding",
    "other"
}

VALID_STATUSES = {
    "unverified", "partially_verified", "verified", "contradicted"
}

TOP_LEVEL_FIELDS = {
    "project_name", "website", "x_account", "discord_url",
    "chain", "category", "discovery_source", "discovery_query",
    "discovered_at", "claims", "unknowns", "risk_notes"
}

CLAIM_FIELDS = {
    "claim", "source", "evidence_type",
    "evidence_status", "confidence"
}


def normalize(value):
    return re.sub(r"\s+", " ", str(value or "").strip()).lower()


def make_project_id(item):
    identity = "|".join([
        normalize(item.get("project_name")),
        normalize(item.get("chain")),
        normalize(item.get("website"))
    ])
    return re.sub(r"[^a-z0-9]+", "-", identity).strip("-")


def make_evidence_id(project_id, claim_text, source):
    identity = f"{project_id}|{normalize(claim_text)}|{normalize(source)}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)

    # Preserve any additional columns already present in older CSV files.
    all_fields = list(fields)
    for row in rows:
        for key in row:
            if key not in all_fields:
                all_fields.append(key)

    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields)
        writer.writeheader()
        writer.writerows(rows)


def validate_item(item):
    if not isinstance(item, dict):
        return "Record must be a JSON object."

    extra = set(item) - TOP_LEVEL_FIELDS
    if extra:
        return f"Unknown top-level fields: {', '.join(sorted(extra))}"

    required = {"project_name", "discovery_source", "discovered_at", "claims"}
    missing = required - set(item)
    if missing:
        return f"Missing required fields: {', '.join(sorted(missing))}"

    if not isinstance(item["project_name"], str) or not item["project_name"].strip():
        return "project_name must be a non-empty string."

    if not isinstance(item["discovery_source"], str):
        return "discovery_source must be a string."

    try:
        timestamp = item["discovered_at"]
        if not isinstance(timestamp, str):
            raise ValueError()
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
    except (ValueError, TypeError):
        return "discovered_at must be a date-time with timezone."

    for field in ("website", "x_account", "discord_url", "chain", "discovery_query"):
        if field in item and item[field] is not None and not isinstance(item[field], str):
            return f"{field} must be a string or null."

    if "category" in item:
        if not isinstance(item["category"], list) or not all(
            isinstance(value, str) for value in item["category"]
        ):
            return "category must be an array of strings."

    for field in ("unknowns", "risk_notes"):
        if field in item and (
            not isinstance(item[field], list)
            or not all(isinstance(value, str) for value in item[field])
        ):
            return f"{field} must be an array of strings."

    if not isinstance(item["claims"], list):
        return "claims must be an array."

    for index, claim in enumerate(item["claims"]):
        if not isinstance(claim, dict):
            return f"Claim {index + 1} must be an object."

        extra_claim_fields = set(claim) - CLAIM_FIELDS
        if extra_claim_fields:
            return f"Claim {index + 1} has unknown fields: {', '.join(sorted(extra_claim_fields))}"

        for field in ("claim", "source", "evidence_type"):
            if field not in claim:
                return f"Claim {index + 1} is missing {field}."

        if not isinstance(claim["claim"], str) or not isinstance(claim["source"], str):
            return f"Claim {index + 1}: claim and source must be strings."

        if claim["evidence_type"] not in VALID_EVIDENCE_TYPES:
            return f"Claim {index + 1} has invalid evidence_type."

        if "evidence_status" in claim and claim["evidence_status"] not in VALID_STATUSES:
            return f"Claim {index + 1} has invalid evidence_status."

        confidence = claim.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                return f"Claim {index + 1}: confidence must be a number or null."
            if not 0 <= confidence <= 1:
                return f"Claim {index + 1}: confidence must be between 0 and 1."

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Import validated Grok research into the database."
    )
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        raise SystemExit("Input file not found.")

    projects = read_csv(PROJECT_FILE)
    evidence = read_csv(EVIDENCE_FILE)

    project_ids = {row.get("project_id", "") for row in projects}
    evidence_ids = {row.get("evidence_id", "") for row in evidence}

    added_projects = 0
    added_evidence = 0
    skipped = 0

    with input_file.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as error:
                print(f"Line {line_number}: invalid JSON ({error.msg})")
                skipped += 1
                continue

            error = validate_item(item)
            if error:
                print(f"Line {line_number}: {error}")
                skipped += 1
                continue

            project_id = make_project_id(item)
            if not project_id:
                print(f"Line {line_number}: could not generate project ID.")
                skipped += 1
                continue

            category = ", ".join(item.get("category", []))

            if project_id not in project_ids:
                projects.append({
                    "project_id": project_id,
                    "project_name": item["project_name"].strip(),
                    "website": item.get("website") or "",
                    "x_account": item.get("x_account") or "",
                    "discord_url": item.get("discord_url") or "",
                    "chain": item.get("chain") or "",
                    "category": category,
                    "first_seen_at": item["discovered_at"],
                    "discovery_source": item["discovery_source"],
                    "discovery_query": item.get("discovery_query") or "",
                    "initial_status": "discovered",
                    "verification_status": "unverified",
                    "notes": "Imported from Grok research"
                })
                project_ids.add(project_id)
                added_projects += 1

            for claim in item["claims"]:
                claim_text = claim["claim"].strip()
                source = claim["source"].strip()

                if not claim_text or not source:
                    skipped += 1
                    continue

                evidence_id = make_evidence_id(project_id, claim_text, source)

                if evidence_id in evidence_ids:
                    continue

                evidence.append({
                    "evidence_id": evidence_id,
                    "entity_id": project_id,
                    "evidence_type": claim["evidence_type"],
                    "claim": claim_text,
                    "source": source,
                    "source_type": item["discovery_source"],
                    "evidence_status": claim.get("evidence_status", "unverified"),
                    "confidence": claim.get("confidence") if claim.get("confidence") is not None else "",
                    "observed_at": item["discovered_at"],
                    "raw_data_reference": "",
                    "notes": "Imported from Grok research"
                })

                evidence_ids.add(evidence_id)
                added_evidence += 1

    write_csv(PROJECT_FILE, PROJECT_FIELDS, projects)
    write_csv(EVIDENCE_FILE, EVIDENCE_FIELDS, evidence)

    print("Grok ingestion completed.")
    print(f"New projects: {added_projects}")
    print(f"New evidence: {added_evidence}")
    print(f"Skipped records: {skipped}")


if __name__ == "__main__":
    main()
