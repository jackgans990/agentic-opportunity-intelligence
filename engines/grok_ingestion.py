import argparse
import csv
import json
import re
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
    return make_project_id({"project_name": identity})


def read_csv(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Import structured Grok research into the database."
    )
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    input_file = Path(args.input)
    if not input_file.exists():
        raise SystemExit("Input file not found.")

    projects = read_csv(PROJECT_FILE)
    evidence = read_csv(EVIDENCE_FILE)

    project_ids = {r["project_id"] for r in projects}
    evidence_ids = {r["evidence_id"] for r in evidence}

    added_projects = 0
    added_evidence = 0
    skipped = 0

    with input_file.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, 1):
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

            name = str(item.get("project_name") or "").strip()
            if not name:
                skipped += 1
                continue

            project_id = make_project_id(item)

            category = item.get("category", [])
            if isinstance(category, list):
                category = ", ".join(str(x) for x in category)
            elif category is None:
                category = ""
            else:
                category = str(category)

            if project_id not in project_ids:
                projects.append({
                    "project_id": project_id,
                    "project_name": name,
                    "website": item.get("website") or "",
                    "x_account": item.get("x_account") or "",
                    "discord_url": item.get("discord_url") or "",
                    "chain": item.get("chain") or "",
                    "category": category,
                    "first_seen_at": item.get("discovered_at", ""),
                    "discovery_source": item.get("discovery_source", ""),
                    "discovery_query": item.get("discovery_query") or "",
                    "initial_status": "discovered",
                    "verification_status": "unverified",
                    "notes": "Imported from Grok research"
                })
                project_ids.add(project_id)
                added_projects += 1

            claims = item.get("claims", [])
            if not isinstance(claims, list):
                skipped += 1
                continue

            for claim in claims:
                if not isinstance(claim, dict):
                    skipped += 1
                    continue

                claim_text = str(claim.get("claim") or "").strip()
                source = str(claim.get("source") or "").strip()

                if not claim_text or not source:
                    skipped += 1
                    continue

                evidence_id = make_evidence_id(
                    project_id, claim_text, source
                )

                if evidence_id in evidence_ids:
                    continue

                evidence_type = claim.get("evidence_type", "other")
                if evidence_type not in VALID_EVIDENCE_TYPES:
                    evidence_type = "other"

                status = claim.get("evidence_status", "unverified")
                if status not in VALID_STATUSES:
                    status = "unverified"

                confidence = claim.get("confidence")
                if not isinstance(confidence, (int, float)):
                    confidence = ""

                evidence.append({
                    "evidence_id": evidence_id,
                    "entity_id": project_id,
                    "evidence_type": evidence_type,
                    "claim": claim_text,
                    "source": source,
                    "source_type": item.get("discovery_source", ""),
                    "evidence_status": status,
                    "confidence": confidence,
                    "observed_at": item.get("discovered_at", ""),
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
