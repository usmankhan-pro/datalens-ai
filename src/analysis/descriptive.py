"""Descriptive statistics for the whole dataset and individual columns."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


def dataset_overview(data: pd.DataFrame) -> dict[str, Any]:
    """Return high-level dataset statistics."""
    n_rows, n_cols = data.shape
    memory_bytes = int(data.memory_usage(index=True, deep=True).sum())
    n_missing = int(data.isna().sum().sum())
    n_duplicates = int(data.duplicated().sum())

    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    categorical_cols = data.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    datetime_cols = data.select_dtypes(include=["datetime", "datetimetz"]).columns.tolist()

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "memory_bytes": memory_bytes,
        "memory_mb": round(memory_bytes / (1024 * 1024), 2),
        "n_missing_cells": n_missing,
        "missing_pct": round(n_missing / (n_rows * n_cols) * 100, 2) if n_rows * n_cols > 0 else 0.0,
        "n_duplicates": n_duplicates,
        "duplicate_pct": round(n_duplicates / n_rows * 100, 2) if n_rows > 0 else 0.0,
        "n_numeric": len(numeric_cols),
        "n_categorical": len(categorical_cols),
        "n_datetime": len(datetime_cols),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "datetime_columns": datetime_cols,
    }


def column_profile(series: pd.Series) -> dict[str, Any]:
    """Return a complete profile for one column."""
    n_rows = len(series)
    n_missing = int(series.isna().sum())
    n_unique = int(series.nunique(dropna=True))
    dtype_str = str(series.dtype)
    non_null = series.dropna()

    profile: dict[str, Any] = {
        "dtype": dtype_str,
        "n_rows": n_rows,
        "n_missing": n_missing,
        "n_non_null": n_rows - n_missing,
        "n_unique": n_unique,
        "missing_pct": round(n_missing / n_rows * 100, 2) if n_rows > 0 else 0.0,
        "unique_pct": round(n_unique / max(n_rows - n_missing, 1) * 100, 2),
        "is_numeric": is_numeric_dtype(series.dtype),
        "is_datetime": is_datetime64_any_dtype(series.dtype),
        "is_all_null": series.isna().all(),
        "is_constant": n_unique == 1 and not series.isna().all(),
    }

    if non_null.empty:
        return profile

    if is_numeric_dtype(series.dtype):
        numeric = non_null.astype(float)
        profile.update({
            "min": float(numeric.min()),
            "max": float(numeric.max()),
            "mean": float(numeric.mean()),
            "median": float(numeric.median()),
            "std": float(numeric.std()),
            "q1": float(numeric.quantile(0.25)),
            "q3": float(numeric.quantile(0.75)),
            "iqr": float(numeric.quantile(0.75) - numeric.quantile(0.25)),
            "skewness": float(numeric.skew()),
        })
    elif is_datetime64_any_dtype(series.dtype):
        profile.update({
            "date_min": str(non_null.min()),
            "date_max": str(non_null.max()),
            "date_range_days": (non_null.max() - non_null.min()).days,
        })
    else:
        top = series.value_counts(dropna=True).head(10)
        profile["top_categories"] = {str(k): int(v) for k, v in top.items()}
        profile["top_category"] = str(top.index[0]) if not top.empty else None
        profile["top_category_count"] = int(top.iloc[0]) if not top.empty else 0

    return profile


def all_column_profiles(data: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Return profiles for all columns."""
    return {str(col): column_profile(data[col]) for col in data.columns}
