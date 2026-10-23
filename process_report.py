
import json
import sys
from pathlib import Path

import pandas as pd


ALLOWED_STATUSES = {"Completed", "Pending"}

REQUIRED_COLUMNS = [
    "transaction_id",
    "region",
    "amount",
    "status",
    "transaction_date",
]


def process_report(file_path):
    source = Path(file_path)

    # 1. Check the input file.
    if not source.exists():
        raise FileNotFoundError(f"CSV file not found: {source}")

    # 2. Read the original CSV.
    original_df = pd.read_csv(source)
    original_rows = len(original_df)

    # 3. Profile the original data.
    missing_values_original = {
        column: int(count)
        for column, count in original_df.isna().sum().items()
    }

    profile = {
        "file_name": source.name,
        "row_count": int(original_rows),
        "column_count": int(len(original_df.columns)),
        "columns": list(original_df.columns),
        "data_types": {
            column: str(dtype)
            for column, dtype in original_df.dtypes.items()
        },
        "missing_values": missing_values_original,
        "exact_duplicate_rows": int(
            original_df.duplicated().sum()
        ),
    }

    if "amount" in original_df.columns:
        original_amounts = pd.to_numeric(
            original_df["amount"], errors="coerce"
        )

        profile["amount_statistics"] = {
            "valid_amount_count": int(
                original_amounts.notna().sum()
            ),
            "missing_or_invalid_amount_count": int(
                original_amounts.isna().sum()
            ),
            "total_amount": (
                round(float(original_amounts.sum()), 2)
                if original_amounts.notna().any()
                else None
            ),
            "average_amount": (
                round(float(original_amounts.mean()), 2)
                if original_amounts.notna().any()
                else None
            ),
        }

    # 4. Check required columns.
    missing_columns = [
        column for column in REQUIRED_COLUMNS
        if column not in original_df.columns
    ]

    row_issues = []
    duplicate_ids = []

    # 5. Validate records if all required columns exist.
    if not missing_columns:
        transaction_ids = (
            original_df["transaction_id"]
            .astype("string")
            .str.strip()
        )
        regions = (
            original_df["region"]
            .astype("string")
            .str.strip()
        )
        statuses = (
            original_df["status"]
            .astype("string")
            .str.strip()
        )
        amounts = pd.to_numeric(
            original_df["amount"], errors="coerce"
        )
        dates = pd.to_datetime(
            original_df["transaction_date"],
            errors="coerce",
        )

        for index in original_df.index:
            issues = []
            row_number = int(index) + 2

            transaction_id = transaction_ids.loc[index]
            region = regions.loc[index]
            status = statuses.loc[index]
            amount = amounts.loc[index]
            date = dates.loc[index]

            if pd.isna(transaction_id) or not transaction_id:
                issues.append("Missing transaction_id")

            if pd.isna(region) or not region:
                issues.append("Missing region")

            if pd.isna(amount):
                issues.append("Missing or invalid amount")
            elif amount <= 0:
                issues.append("Amount must be greater than zero")

            if pd.isna(status) or not status:
                issues.append("Missing status")
            elif status not in ALLOWED_STATUSES:
                issues.append("Invalid status")

            if pd.isna(date):
                issues.append(
                    "Missing or invalid transaction_date"
                )

            if issues:
                row_issues.append({
                    "row_number": row_number,
                    "transaction_id": (
                        None if pd.isna(transaction_id)
                        else str(transaction_id)
                    ),
                    "issues": issues,
                })

        # Identify duplicate IDs in the original input.
        valid_ids = transaction_ids.fillna("").str.strip()
        duplicate_mask = (
            valid_ids.ne("")
            & valid_ids.duplicated(keep=False)
        )
        duplicate_ids = sorted(
            valid_ids[duplicate_mask].unique().tolist()
        )

    validation = {
        "missing_columns": missing_columns,
        "invalid_row_count": len(row_issues),
        "row_issues": row_issues,
        "duplicate_transaction_ids": duplicate_ids,
        "duplicate_transaction_id_count": len(duplicate_ids),
        "validation_passed": (
            not missing_columns
            and not row_issues
            and not duplicate_ids
        ),
    }

    # 6. Remove only exact duplicate rows.
    cleaned_df = original_df.drop_duplicates().copy()
    duplicates_removed = original_rows - len(cleaned_df)

    # 7. Normalize data types in the cleaned output.
    if "amount" in cleaned_df.columns:
        cleaned_df["amount"] = pd.to_numeric(
            cleaned_df["amount"], errors="coerce"
        )

    if "transaction_date" in cleaned_df.columns:
        cleaned_df["transaction_date"] = pd.to_datetime(
            cleaned_df["transaction_date"],
            errors="coerce",
        )

    missing_values_cleaned = {
        column: int(count)
        for column, count in cleaned_df.isna().sum().items()
        if count > 0
    }

    # 8. Prepare output filenames.
    cleaned_path = source.with_name(
        f"{source.stem}_cleaned.csv"
    )
    report_path = source.with_name(
        f"{source.stem}_processing_report.json"
    )

    # 9. Save the cleaned CSV.
    cleaned_df.to_csv(
        cleaned_path,
        index=False,
        date_format="%Y-%m-%d",
    )

    # 10. Decide the final processing status.
    review_required = bool(
        missing_columns
        or row_issues
        or duplicate_ids
        or missing_values_cleaned
    )

    final_status = (
        "NeedsReview" if review_required else "Completed"
    )

    # 11. Build the integrated report.
    report = {
        "input_file": source.name,
        "processing_status": final_status,
        "review_required": review_required,
        "profile": profile,
        "validation": validation,
        "cleaning": {
            "output_file": cleaned_path.name,
            "original_rows": int(original_rows),
            "cleaned_rows": int(len(cleaned_df)),
            "exact_duplicate_rows_removed": int(
                duplicates_removed
            ),
            "missing_values_after_cleaning": (
                missing_values_cleaned
            ),
        },
    }

    # 12. Save the JSON report.
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    report["report_file"] = report_path.name

    # Include the report filename in the saved JSON too.
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python process_report.py <path-to-csv>",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        result = process_report(sys.argv[1])
        print(json.dumps(result, indent=2))

    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
