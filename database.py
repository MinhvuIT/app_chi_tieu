"""Supabase persistence layer for personal finance transactions."""

from datetime import date
import math
from urllib.parse import urlparse

import pandas as pd
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError
from supabase import Client, create_client


COLUMNS = ["id", "date", "amount", "category", "type", "note"]
TRANSACTION_TYPES = {"Chi tiêu", "Thu nhập"}
PAGE_SIZE = 500


@st.cache_resource
def get_client() -> Client:
    """Create and cache the Supabase client from Streamlit secrets."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except (KeyError, StreamlitSecretNotFoundError) as error:
        raise RuntimeError(
            "Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong Streamlit secrets."
        ) from error

    if not isinstance(url, str) or not url.strip():
        raise RuntimeError("SUPABASE_URL phải là chuỗi không rỗng.")
    if not isinstance(key, str) or not key.strip():
        raise RuntimeError("SUPABASE_KEY phải là chuỗi không rỗng.")

    url = url.strip()
    parsed_url = urlparse(url)
    if not parsed_url.netloc or parsed_url.scheme not in {"https", "http"}:
        raise RuntimeError("SUPABASE_URL phải là URL http(s) hợp lệ.")
    if parsed_url.scheme != "https" and parsed_url.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise RuntimeError("SUPABASE_URL phải dùng HTTPS khi kết nối từ xa.")

    return create_client(url.rstrip("/"), key.strip())


def get_transactions() -> pd.DataFrame:
    """Load transactions from Supabase using the dashboard's expected schema."""
    client = get_client()
    records = []
    offset = 0
    while True:
        page = (
            client.table("transactions")
            .select(",".join(COLUMNS))
            .order("id")
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
            .data
        )
        if not isinstance(page, list):
            raise RuntimeError("Supabase trả về dữ liệu giao dịch không hợp lệ.")
        records.extend(page)
        if len(page) < PAGE_SIZE:
            break
        offset += len(page)

    transactions = pd.DataFrame.from_records(records, columns=COLUMNS)
    transaction_ids = pd.to_numeric(transactions["id"], errors="raise")
    if transaction_ids.isna().any() or (transaction_ids % 1 != 0).any():
        raise ValueError("Transaction IDs must be non-empty integers.")
    transactions["id"] = transaction_ids.astype("int64")
    transactions["date"] = pd.to_datetime(transactions["date"], errors="raise")
    transactions["amount"] = pd.to_numeric(
        transactions["amount"], errors="raise"
    ).astype(float)
    if not transactions["type"].isin(TRANSACTION_TYPES).all():
        raise ValueError("Transaction type must be 'Chi tiêu' or 'Thu nhập'.")

    return transactions


def add_transaction(
    amount: float,
    category: str,
    transaction_type: str,
    note: str,
) -> None:
    """Validate and save a transaction dated with the current system date."""
    if isinstance(amount, bool):
        raise ValueError("Amount must be a positive finite number.")
    try:
        amount = float(amount)
    except (TypeError, ValueError) as error:
        raise ValueError("Amount must be a positive finite number.") from error
    if not math.isfinite(amount) or amount <= 0:
        raise ValueError("Amount must be a positive finite number.")

    if not isinstance(category, str) or not category.strip():
        raise ValueError("Category must not be empty.")
    if transaction_type not in TRANSACTION_TYPES:
        raise ValueError("Transaction type must be 'Chi tiêu' or 'Thu nhập'.")
    if not isinstance(note, str) or not note.strip():
        raise ValueError("Note must not be empty.")

    get_client().table("transactions").insert(
        {
            "date": date.today().isoformat(),
            "amount": amount,
            "category": category.strip(),
            "type": transaction_type,
            "note": note.strip(),
        }
    ).execute()
