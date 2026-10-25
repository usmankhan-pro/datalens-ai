"""Streamlit entry point and backwards-compatible dataset utilities."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st

DEMO_PATH = Path(__file__).parent / "data" / "telco_churn.csv"


def csv_bytes(data: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as UTF-8 CSV without its index."""
    return data.to_csv(index=False).encode("utf-8")


def excel_bytes(data: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as an in-memory Excel workbook."""
    buffer = BytesIO()
    data.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def log_csv_bytes(records: list[dict[str, object]]) -> bytes:
    """Serialize legacy cleaning-log records."""
    columns = ["step", "column", "rows_affected"]
    return pd.DataFrame(records, columns=columns).to_csv(index=False).encode("utf-8")


def read_table(source: BinaryIO, filename: str) -> pd.DataFrame:
    """Load a CSV or Excel table using the validated shared loader."""
    from src.data.loader import load_table

    data, _ = load_table(source, filename)
    return data


def normalize_blank_cells(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize blank or whitespace-only cells to pandas missing values."""
    return data.replace(r"^\s*$", pd.NA, regex=True)


def load_demo() -> pd.DataFrame:
    """Load the bundled Telco demo while retaining its raw numeric-string column."""
    data = pd.read_csv(DEMO_PATH, dtype={"TotalCharges": str}, skipinitialspace=True)
    return normalize_blank_cells(data)


def main() -> None:
    st.set_page_config(page_title="DataFlow Analytics", page_icon="📊", layout="wide")
    from src.ui import run_app

    run_app()


if __name__ == "__main__":
    main()
