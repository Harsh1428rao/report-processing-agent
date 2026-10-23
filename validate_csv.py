
import json
import sys
from pathlib import Path

import pandas as pd


ALLOWED_STATUSES = {"Completed", "Pending"}


def validate_csv(file_path):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)

    required_columns = [
        "transaction_id",
        "region",
        "amount",
        "status",
        "transaction_date",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        return {
            "file_name": path.name,
            "validation_passed": False,
            "missing_columns": missing_columns,
            "errors": [
                "Required columns are missing. "
                "Record-level validation was not performed."
            ],
        }

    # Normalize text fields for validation.
    transaction_id = df["transaction_id"].astype("string").str.strip()
    region = df["region"].astype("string").str.strip()
    status = df["status"].astype("string").str.strip()

    # Convert values for checking without changing the source CSV.
    amount = pd.to_numeric(df["amount"], errors="coerce")
    dates = pd.to_datetime(
        df["transaction_date"], errors="coerce"
    )

    issues = []

    for index in df.index:
        row_number = int(index) + 2  # Header is row 1.
        row_issues = []

        if pd.isna(transaction_id.loc[index]) or not transaction_id.loc[index]:
            row_issues.append("Missing transaction_id")

        if pd.isna(region.loc[index]) or not region.loc[index]:
            row_issues.append("Missing region")

        if pd.isna(amount.loc[index]):
            row_issues.append("Missing or invalid amount")
        elif amount.loc[index] <= 0:
            row_issues.append("Amount must be greater than zero")

        if pd.isna(status.loc[index]) or not status.loc[index]:
            row_issues.append("Missing status")
        elif status.loc[index] not in ALLOWED_STATUSES:
            row_issues.append("Invalid status")

        if pd.isna(dates.loc[index]):
            row_issues.append("Missing or invalid transaction_date")

        if row_issues:
            issues.append({
                "row_number": row_number,
                "transaction_id": (
                    None if pd.isna(transaction_id.loc[index])
                    else str(transaction_id.loc[index])
                ),
                "issues": row_issues,
            })

    # Flag every row belonging to a repeated transaction ID.
    valid_ids = transaction_id.fillna("").str.strip()
    duplicate_mask = (
        valid_ids.ne("")
        & valid_ids.duplicated(keep=False)
    )

    duplicate_ids = sorted(
        valid_ids[duplicate_mask].unique().tolist()
    )

    report = {
        "file_name": path.name,
        "total_rows": int(len(df)),
        "validation_passed": len(issues) == 0 and len(duplicate_ids) == 0,
        "missing_columns": [],
        "invalid_row_count": len(issues),
        "row_issues": issues,
        "duplicate_transaction_ids": duplicate_ids,
        "duplicate_transaction_id_count": len(duplicate_ids),
        "review_required": len(issues) > 0 or len(duplicate_ids) > 0,
    }

    report_path = path.with_name(
        f"{path.stem}_validation_report.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python validate_csv.py <path-to-csv>",
            file=sys.stderr
        )
        sys.exit(1)

    try:
        result = validate_csv(sys.argv[1])
        print(json.dumps(result, indent=2))
    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
