
import json
import sys
from pathlib import Path

import pandas as pd


def profile_csv(file_path):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path)

    # Basic dataset information
    profile = {
        "file_name": path.name,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "data_types": {
            column: str(dtype)
            for column, dtype in df.dtypes.items()
        },
        "missing_values": {
            column: int(count)
            for column, count in df.isna().sum().items()
        },
        "duplicate_rows": int(df.duplicated().sum()),
    }

    # Check duplicate transaction IDs if the column exists
    if "transaction_id" in df.columns:
        profile["duplicate_transaction_ids"] = int(
            df["transaction_id"].duplicated().sum()
        )

    # Calculate sales statistics when amount exists
    if "amount" in df.columns:
        amounts = pd.to_numeric(df["amount"], errors="coerce")

        profile["amount_statistics"] = {
            "valid_amount_count": int(amounts.notna().sum()),
            "missing_or_invalid_amount_count": int(amounts.isna().sum()),
            "total_amount": (
                round(float(amounts.sum()), 2)
                if amounts.notna().any()
                else None
            ),
            "average_amount": (
                round(float(amounts.mean()), 2)
                if amounts.notna().any()
                else None
            ),
        }

    return profile


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python profile_csv.py <path-to-csv>")
        sys.exit(1)

    try:
        result = profile_csv(sys.argv[1])
        print(json.dumps(result, indent=2))
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
