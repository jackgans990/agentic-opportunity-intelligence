import argparse
import json
from pathlib import Path

REQUIRED_CHECKS = [
    "contract_verified",
    "transaction_simulation_passed",
    "no_token_approval",
    "no_hidden_payment",
    "no_unexpected_asset_transfer",
    "no_ambiguous_signature",
    "safe_contract_permissions",
    "wallet_balance_sufficient_for_gas",
]

def assess_security(item):
    results = item.get("checks", {})

    passed = []
    failed = []
    unknown = []

    for check in REQUIRED_CHECKS:
        value = results.get(check)

        if value is True:
            passed.append(check)
        elif value is False:
            failed.append(check)
        else:
            unknown.append(check)

    if failed:
        status = "blocked"
    elif unknown:
        status = "not_ready"
    else:
        status = "ready"

    return {
        "project_id": item.get("project_id", ""),
        "security_status": status,
        "passed_checks": passed,
        "failed_checks": failed,
        "unknown_checks": unknown,
        "execution_allowed": status == "ready",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate transaction security readiness."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSONL file containing security check results."
    )

    args = parser.parse_args()
    input_file = Path(args.input)

    if not input_file.exists():
        raise SystemExit(f"Input file not found: {input_file}")

    processed = 0

    with input_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"Invalid JSON at line {line_number}")
                continue

            if not isinstance(item, dict):
                continue

            result = assess_security(item)

            print(json.dumps(result, ensure_ascii=False))
            processed += 1

    print(f"Security assessments completed: {processed}")


if __name__ == "__main__":
    main()
