
import json
import sys
from pathlib import Path

import pandas as pd


def clean_csv(file_path):
    source = Path(file_path)

    # 1. Check that the input file exists.
    if not source.exists():
        raise FileNotFoundError(f"CSV file not found: {source}")

    # 2. Read the CSV.
    df = pd.read_csv(source)
    original_rows = len(df)

    # 3. Count repeated transaction IDs BEFORE cleaning.
    original_duplicate_id_rows = 0

    if "transaction_id" in df.columns:
        original_duplicate_id_rows = int(
            df["transaction_id"].duplicated(keep=False).sum()
        )

    # 4. Remove only completely identical rows.
    df = df.drop_duplicates().copy()
    exact_duplicates_removed = original_rows - len(df)

    # 5. Convert amounts to numeric values.
    # Invalid amounts become missing values for review.
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(
            df["amount"], errors="coerce"
        )

    # 6. Convert transaction dates to date values.
    # Invalid dates become missing values for review.
    if "transaction_date" in df.columns:
        df["transaction_date"] = pd.to_datetime(
            df["transaction_date"], errors="coerce"
        )

    # 7. Count repeated transaction IDs AFTER cleaning.
    remaining_duplicate_id_rows = 0

    if "transaction_id" in df.columns:
        remaining_duplicate_id_rows = int(
            df["transaction_id"].duplicated(keep=False).sum()
        )

    # 8. Identify missing values after cleaning.
    missing_values = {
        column: int(count)
        for column, count in df.isna().sum().items()
        if count > 0
    }

    # 9. Create output file paths.
    output_path = source.with_name(
        f"{source.stem}_cleaned.csv"
    )

    report_path = source.with_name(
        f"{source.stem}_quality_report.json"
    )

    # 10. Save the cleaned CSV.
    df.to_csv(
        output_path,
        index=False,
        date_format="%Y-%m-%d"
    )

    # 11. Generate the quality report.
    report = {
        "input_file": source.name,
        "output_file": output_path.name,
        "original_rows": int(original_rows),
        "cleaned_rows": int(len(df)),
        "exact_duplicate_rows_removed": int(
            exact_duplicates_removed
        ),
        "rows_with_repeated_transaction_ids_before_cleaning":
            original_duplicate_id_rows,
        "rows_with_repeated_transaction_ids_after_cleaning":
            remaining_duplicate_id_rows,
        "missing_values_after_cleaning": missing_values,
        "review_required": bool(
            missing_values or remaining_duplicate_id_rows
        )
    }

    # 12. Save the JSON quality report.
    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(
            "Usage: python clean_csv.py <path-to-csv>",
            file=sys.stderr
        )
        sys.exit(1)

    try:
        result = clean_csv(sys.argv[1])
        print(json.dumps(result, indent=2))

    except (
        FileNotFoundError,
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError,
    ) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
