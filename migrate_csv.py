"""Import the existing local transactions CSV into an empty Supabase table."""

from pathlib import Path
import math
import tomllib
from urllib.parse import urlparse

import pandas as pd
from supabase import Client, create_client


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "transactions.csv"
SECRETS_PATH = ROOT / ".streamlit" / "secrets.toml"
COLUMNS = ["id", "date", "amount", "category", "type", "note"]
BATCH_SIZE = 500


def _create_supabase_client(url: object, key: object) -> Client:
    """Validate Supabase credentials and create a normalized client."""
    if not isinstance(url, str) or not url.strip():
        raise RuntimeError("SUPABASE_URL must be a non-empty string.")
    if not isinstance(key, str) or not key.strip():
        raise RuntimeError("SUPABASE_KEY must be a non-empty string.")

    url = url.strip()
    parsed_url = urlparse(url)
    if not parsed_url.netloc or parsed_url.scheme not in {"https", "http"}:
        raise RuntimeError("SUPABASE_URL must be a valid HTTP(S) URL.")
    if parsed_url.scheme != "https" and parsed_url.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeError("SUPABASE_URL must use HTTPS for remote connections.")

    return create_client(url.rstrip("/"), key.strip())


def main() -> None:
    """Validate local data, then import it once into the configured Supabase."""
    with SECRETS_PATH.open("rb") as secrets_file:
        secrets = tomllib.load(secrets_file)
    try:
        url = secrets["SUPABASE_URL"]
        key = secrets["SUPABASE_KEY"]
    except KeyError as error:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in "
            ".streamlit/secrets.toml."
        ) from error

    transactions = pd.read_csv(CSV_PATH)
    if list(transactions.columns) != COLUMNS:
        raise ValueError(f"Invalid transaction CSV schema. Expected {COLUMNS}.")

    transaction_ids = pd.to_numeric(transactions["id"], errors="raise")
    if (
        transaction_ids.isna().any()
        or (transaction_ids % 1 != 0).any()
        or transaction_ids.duplicated().any()
    ):
        raise ValueError("Transaction IDs must be unique non-empty integers.")
    if not transactions["type"].isin({"Chi tiêu", "Thu nhập"}).all():
        raise ValueError("Transaction type must be 'Chi tiêu' or 'Thu nhập'.")

    transactions["date"] = pd.to_datetime(
        transactions["date"], errors="raise"
    ).dt.strftime("%Y-%m-%d")
    transactions["amount"] = pd.to_numeric(
        transactions["amount"], errors="raise"
    ).astype(float)
    if not transactions["amount"].map(
        lambda amount: math.isfinite(amount) and amount > 0
    ).all():
        raise ValueError("All transaction amounts must be positive finite numbers.")
    for column in ("category", "note"):
        if transactions[column].isna().any() or not transactions[column].map(
            lambda value: isinstance(value, str) and bool(value.strip())
        ).all():
            raise ValueError(f"{column.title()} must not be empty.")

    client = _create_supabase_client(url, key)
    transactions_table = client.schema("public").table("transactions")
    existing = (
        transactions_table.select("id").limit(1).execute().data
    )
    if not isinstance(existing, list):
        raise RuntimeError("Supabase returned an invalid transaction response.")
    if existing:
        raise RuntimeError(
            "The Supabase transactions table is not empty; refusing to import "
            "to prevent duplicate or overwritten data."
        )

    records = transactions.drop(columns=["id"]).to_dict(orient="records")
    for start in range(0, len(records), BATCH_SIZE):
        batch = records[start : start + BATCH_SIZE]
        inserted = transactions_table.insert(batch).execute().data
        if not isinstance(inserted, list) or len(inserted) != len(batch):
            raise RuntimeError("Supabase did not confirm every imported row.")

    print(f"Imported {len(records)} transactions into Supabase.")


if __name__ == "__main__":
    main()
