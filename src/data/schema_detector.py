"""Schema detection: identifies column types, identifiers, and structural issues."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from src.cleaning.data_types import detect_column_types


def detect_schema(data: pd.DataFrame) -> dict[str, Any]:
    """Return a full schema description for a DataFrame.

    Includes per-column type inference, identifier candidates, empty/constant
    columns, and duplicate column names.
    """
    n_rows, n_cols = data.shape
    col_types = detect_column_types(data)

    columns: list[dict[str, Any]] = []
    identifier_candidates: list[str] = []
    empty_columns: list[str] = []
    constant_columns: list[str] = []

    seen: set[str] = set()
    duplicate_column_names: list[str] = []

    for col in data.columns:
        col_str = str(col)
        if col_str in seen:
            duplicate_column_names.append(col_str)
        seen.add(col_str)

        info = col_types.get(col_str, {})
        col_info = {
            "name": col_str,
            "position": len(columns),
            "dtype": str(data[col].dtype),
            "inferred_type": info.get("inferred_type", "unknown"),
            "confidence": info.get("confidence", 0.0),
            "n_missing": int(data[col].isna().sum()),
            "n_unique": int(data[col].nunique(dropna=True)),
            "is_identifier_candidate": info.get("is_identifier_candidate", False),
            "is_numeric_string": info.get("is_numeric_string", False),
            "is_date_string": info.get("is_date_string", False),
            "is_all_null": data[col].isna().all(),
            "is_constant": (
                not data[col].isna().all()
                and data[col].nunique(dropna=True) <= 1
            ),
        }
        columns.append(col_info)

        if col_info["is_identifier_candidate"]:
            identifier_candidates.append(col_str)
        if col_info["is_all_null"]:
            empty_columns.append(col_str)
        if col_info["is_constant"]:
            constant_columns.append(col_str)

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "n_duplicate_column_names": len(duplicate_column_names),
        "duplicate_column_names": duplicate_column_names,
        "n_identifier_candidates": len(identifier_candidates),
        "identifier_candidates": identifier_candidates,
        "n_empty_columns": len(empty_columns),
        "empty_columns": empty_columns,
        "n_constant_columns": len(constant_columns),
        "constant_columns": constant_columns,
        "columns": columns,
    }


def is_likely_identifier(series: pd.Series, n_rows: int) -> bool:
    """Heuristic: is this column likely an identifier (unique, non-null, index-like)?"""
    if series.isna().all():
        return False
    n_unique = series.nunique(dropna=True)
    n_non_null = len(series) - series.isna().sum()
    return n_unique == n_non_null and n_non_null > 0
