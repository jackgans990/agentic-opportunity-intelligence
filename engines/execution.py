import argparse
import json
from pathlib import Path

FREE_MINT_THRESHOLD = 70
PAID_MINT_THRESHOLD = 90


def assess_execution(item):
    opportunity_type = item.get("opportunity_type", "")
    score = item.get("opportunity_score")
    security_status = item.get("security_status", "not_ready")
    user_approved = item.get("user_approved", False)

    if not isinstance(score, (int, float)):
        return "blocked", "Opportunity score is missing or invalid."

    if security_status != "ready":
        return "blocked", "Security checks are not fully passed."

    if opportunity_type == "free_mint":
        if score < FREE_MINT_THRESHOLD:
            return "not_ready", "Score is below the free mint threshold."

        return (
            "eligible_for_authorization",
            "Free mint passed preliminary checks. Final transaction review required."
        )

    if opportunity_type == "paid_mint":
        if score < PAID_MINT_THRESHOLD:
            return "not_ready", "Score is below the paid mint threshold."

        if user_approved is not True:
            return "awaiting_user_approval", "Explicit user approval is required."

        return (
            "eligible_for_authorization",
            "Paid mint passed preliminary checks and user approval."
        )

    return "blocked", "Unknown opportunity type."


def main():
    parser = argparse.ArgumentParser(
        description="Assess execution eligibility without sending transactions."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSONL file containing execution assessments."
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

            status, reason = assess_execution(item)

            result = {
                "project_id": item.get("project_id", ""),
                "execution_status": status,
                "reason": reason,
                "transaction_sent": False
            }

            print(json.dumps(result, ensure_ascii=False))
            processed += 1

    print(f"Execution assessments completed: {processed}")
    print("No blockchain transactions were sent.")


if __name__ == "__main__":
    main()
