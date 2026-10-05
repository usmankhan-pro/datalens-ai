"""Profiling utilities for DataLens AI.

This module infers column types, summarizes dataset structure, and produces
column-level metadata used by the Data Profile page and quality engine.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

BOOL_VALUES = {"true", "false", "yes", "no", "y", "n", "0", "1", "t", "f"}
ID_HINTS = ("id", "key", "code", "customer", "client", "account", "order", "invoice", "number")
DATE_HINTS = ("date", "time", "day", "month", "year", "created", "updated", "timestamp")
NUMERIC_HINTS = (
    "amount", "revenue", "cost", "price", "profit", "margin",
    "quantity", "qty", "count", "total", "sales", "age", "score",
    "rate", "spend", "value",
)


def _normalize_numeric_string(value: Any) -> Any:
    """Convert common currency/percent string values to numeric floats."""
    if pd.isna(value):
        return np.nan
    text = str(value).strip()
    if text == "":
        return np.nan
    text = text.replace("$", "").replace(",", "").replace("%", "")
    text = text.replace("(", "-").replace(")", "")
    try:
        return float(text)
    except ValueError:
        return np.nan


def _is_bool_like(series: pd.Series) -> bool:
    """Check whether the non-null values are boolean-like."""
    valid = series.dropna().astype(str).str.strip().str.lower()
    if valid.empty:
        return False
    unique = set(valid.tolist())
    return bool(unique.issubset(BOOL_VALUES))


def _parse_date_value(value: Any) -> pd.Timestamp | None:
    """Attempt to parse a single value as a datetime."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return pd.to_datetime(text, errors="raise")
    except (TypeError, ValueError):
        return None


def _get_date_format(series: pd.Series) -> str | None:
    """Try to identify the dominant datetime format from a sample of values."""
    valid_values = series.dropna().astype(str).head(200)
    if valid_values.empty:
        return None

    candidates = [
        "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S",
        "%d-%m-%Y", "%m-%d-%Y", "%Y-%m-%dT%H:%M:%S",
    ]
    counts: Counter[str] = Counter()
    for value in valid_values:
        for fmt in candidates:
            try:
                pd.to_datetime(value, format=fmt)
            except (TypeError, ValueError):
                continue
            counts[fmt] += 1
    if not counts:
        return None
    return counts.most_common(1)[0][0]


def _column_inference(series: pd.Series, column_name: str) -> str:
    """Infer the column type using the project rules."""
    non_null = series.dropna()
    if non_null.empty:
        return "text"

    unique_count = non_null.nunique()
    if unique_count <= 1:
        return "constant"

    if _is_bool_like(series):
        return "boolean"

    numeric_values = non_null.map(_normalize_numeric_string)
    numeric_valid = numeric_values.dropna()
    numeric_ratio = len(numeric_valid) / len(non_null)
    if numeric_ratio >= 0.95:
        return "numeric"

    lower_name = column_name.lower()
    date_hint = any(token in lower_name for token in DATE_HINTS)
    parseable_dates = non_null.map(_parse_date_value)
    date_valid = parseable_dates.dropna()
    date_ratio = len(date_valid) / len(non_null)
    if date_ratio >= 0.90 and (date_hint or date_ratio >= 0.99):
        return "datetime"

    unique_ratio = unique_count / len(non_null)
    if unique_ratio >= 0.95 and (
        any(token in lower_name for token in ID_HINTS)
        or all(re.fullmatch(r"\d+", str(v).strip()) for v in non_null.head(20).astype(str))
    ):
        return "id"

    if unique_count <= 50 or unique_ratio < 0.05:
        return "categorical"

    return "text"


def _mixed_type_flag(series: pd.Series) -> bool:
    """Flag a column if numeric and string values are mixed together."""
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return False
    has_number = non_null.map(lambda x: bool(re.search(r"\d", x))).astype(bool)
    has_letter = non_null.map(lambda x: bool(re.search(r"[A-Za-z]", x))).astype(bool)
    return bool((has_number & has_letter).any() and (has_number | has_letter).any())


def profile_dataframe(df: pd.DataFrame) -> Dict[str, Any]:
    """Return a dataset profile and per-column profile metadata."""
    if df is None or df.empty:
        return {
            "rows": 0,
            "cols": 0,
            "memory_size": 0,
            "duplicate_rows": 0,
            "total_missing_cells": 0,
            "type_counts": {"numeric": 0, "datetime": 0, "categorical": 0, "text": 0, "boolean": 0, "id": 0, "constant": 0},
            "columns": [],
        }

    columns: List[Dict[str, Any]] = []
    type_counts: Counter[str] = Counter()
    columns_by_name: Dict[str, Dict[str, Any]] = {}

    for column_name in df.columns:
        series = df[column_name]
        inferred_type = _column_inference(series, str(column_name))
        type_counts[inferred_type] += 1

        missing_count = int(series.isna().sum())
        if inferred_type == "datetime":
            parsed = series.map(_parse_date_value)
            invalid_count = int(parsed.isna().sum() - series.isna().sum())
        else:
            invalid_count = 0

        column_profile = {
            "column": column_name,
            "dtype": str(series.dtype),
            "inferred_type": inferred_type,
            "unique_count": int(series.nunique(dropna=True)),
            "missing_count": missing_count,
            "missing_pct": float((missing_count / len(df)) * 100) if len(df) else 0.0,
            "constant": bool(series.nunique(dropna=True) <= 1),
            "is_id": inferred_type == "id",
            "sample_values": [str(v) for v in series.dropna().head(5).tolist()],
            "dominant_date_format": _get_date_format(series) if inferred_type == "datetime" else None,
            "mixed_type": _mixed_type_flag(series),
            "invalid_value_count": invalid_count,
        }
        columns.append(column_profile)
        columns_by_name[str(column_name)] = column_profile

    return {
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "memory_size": int(df.memory_usage(deep=True).sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "total_missing_cells": int(df.isna().sum().sum()),
        "type_counts": {
            "numeric": int(type_counts.get("numeric", 0)),
            "datetime": int(type_counts.get("datetime", 0)),
            "categorical": int(type_counts.get("categorical", 0)),
            "text": int(type_counts.get("text", 0)),
            "boolean": int(type_counts.get("boolean", 0)),
            "id": int(type_counts.get("id", 0)),
            "constant": int(type_counts.get("constant", 0)),
        },
        "columns": columns_by_name,
        "column_profiles": columns,
    }


__all__ = ["profile_dataframe"]
