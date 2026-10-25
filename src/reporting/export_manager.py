"""Export manager: download-ready bytes for cleaned data, reports, and logs."""

from __future__ import annotations

from io import BytesIO, StringIO
from typing import Any

import pandas as pd


def dataframe_to_csv_bytes(data: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as UTF-8 CSV without its index."""
    return data.to_csv(index=False).encode("utf-8")


def dataframe_to_excel_bytes(data: pd.DataFrame) -> bytes:
    """Serialize a DataFrame as an in-memory Excel workbook."""
    buffer = BytesIO()
    data.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def report_to_csv_bytes(records: list[dict[str, Any]], columns: list[str]) -> bytes:
    """Serialize a list of records as UTF-8 CSV with explicit columns."""
    df = pd.DataFrame(records, columns=columns) if records else pd.DataFrame(columns=columns)
    return df.to_csv(index=False).encode("utf-8")


def cleaning_log_to_csv_bytes(records: list[dict[str, Any]]) -> bytes:
    """Serialize cleaning audit records as CSV."""
    columns = [
        "step", "column", "operation", "rows_affected",
        "parameters", "before_stats", "after_stats",
        "succeeded", "warning", "timestamp",
    ]
    return report_to_csv_bytes(records, columns)


def quality_report_to_csv_bytes(dimensions: list[dict[str, Any]]) -> bytes:
    """Serialize quality dimension results as CSV."""
    columns = [
        "dimension", "weight", "score", "severity",
        "numerator", "denominator", "effect_on_overall",
        "issues", "recommended_action", "limitation",
    ]
    return report_to_csv_bytes(dimensions, columns)


def export_cleaned_dataset(
    cleaned_data: pd.DataFrame,
    fmt: str = "csv",
) -> tuple[bytes, str, str]:
    """Return (bytes, filename, mime_type) for the cleaned dataset."""
    if fmt == "excel":
        return (
            dataframe_to_excel_bytes(cleaned_data),
            "cleaned_data.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    return (
        dataframe_to_csv_bytes(cleaned_data),
        "cleaned_data.csv",
        "text/csv",
    )


def export_cleaning_log(records: list[dict[str, Any]]) -> tuple[bytes, str, str]:
    """Return (bytes, filename, mime_type) for the cleaning audit log."""
    return (
        cleaning_log_to_csv_bytes(records),
        "cleaning_log.csv",
        "text/csv",
    )


def export_quality_report(dimensions: list[dict[str, Any]]) -> tuple[bytes, str, str]:
    """Return (bytes, filename, mime_type) for the quality score report."""
    return (
        quality_report_to_csv_bytes(dimensions),
        "quality_report.csv",
        "text/csv",
    )
