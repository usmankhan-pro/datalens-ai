"""Univariate analysis for individual columns."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


def numeric_summary(series: pd.Series) -> dict[str, Any]:
    """Summary statistics for a numeric series."""
    values = series.dropna().astype(float)
    if values.empty:
        return {"n": 0, "n_missing": int(series.isna().sum())}

    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - 1.5 * iqr
    upper_fence = q3 + 1.5 * iqr
    n_outliers = int(((values < lower_fence) | (values > upper_fence)).sum())

    return {
        "n": int(len(values)),
        "n_missing": int(series.isna().sum()),
        "n_unique": int(values.nunique()),
        "min": float(values.min()),
        "q1": q1,
        "median": float(values.median()),
        "q3": q3,
        "max": float(values.max()),
        "mean": float(values.mean()),
        "std": float(values.std()),
        "iqr": iqr,
        "skewness": float(values.skew()),
        "n_outliers_iqr": n_outliers,
        "outlier_pct": round(n_outliers / len(values) * 100, 2) if len(values) > 0 else 0.0,
    }


def categorical_summary(series: pd.Series) -> dict[str, Any]:
    """Summary statistics for a categorical/text series."""
    values = series.dropna().astype(str)
    n_missing = int(series.isna().sum())
    n_blank = int(values.map(lambda v: v.strip() == "").sum())

    if values.empty:
        return {
            "n": 0,
            "n_missing": n_missing,
            "n_blank": n_blank,
            "n_unique": 0,
            "top_categories": {},
        }

    counts = values.value_counts()
    top = counts.head(10)

    return {
        "n": int(len(values)),
        "n_missing": n_missing,
        "n_blank": n_blank,
        "n_unique": int(values.nunique()),
        "top_categories": {str(k): int(v) for k, v in top.items()},
        "top_category": str(top.index[0]),
        "top_category_count": int(top.iloc[0]),
        "top_category_pct": round(int(top.iloc[0]) / len(values) * 100, 2),
        "rare_categories": {
            str(k): int(v) for k, v in counts.tail(5).items() if v == 1
        },
    }


def datetime_summary(series: pd.Series) -> dict[str, Any]:
    """Summary statistics for a datetime series."""
    values = pd.to_datetime(series.dropna(), errors="coerce")
    n_missing = int(series.isna().sum())

    if values.empty:
        return {"n": 0, "n_missing": n_missing}

    return {
        "n": int(len(values)),
        "n_missing": n_missing,
        "date_min": str(values.min()),
        "date_max": str(values.max()),
        "date_range_days": int((values.max() - values.min()).days),
        "n_unique": int(values.nunique()),
    }


def boolean_summary(series: pd.Series) -> dict[str, Any]:
    """Summary statistics for a boolean series."""
    values = series.dropna()
    n_true = int(values.astype(bool).sum()) if not values.empty else 0
    n_false = int(len(values) - n_true)

    return {
        "n": int(len(values)),
        "n_missing": int(series.isna().sum()),
        "n_true": n_true,
        "n_false": n_false,
        "true_pct": round(n_true / len(values) * 100, 2) if len(values) > 0 else 0.0,
        "false_pct": round(n_false / len(values) * 100, 2) if len(values) > 0 else 0.0,
    }


def summarize_column(series: pd.Series) -> dict[str, Any]:
    """Dispatch to the correct univariate summary based on inferred type."""
    from src.cleaning.data_types import detect_column_types

    types = detect_column_types(series.to_frame())
    col_name = str(series.name)
    inferred = types.get(col_name, {}).get("inferred_type", "unknown")

    if is_numeric_dtype(series.dtype):
        return numeric_summary(series)
    if is_datetime64_any_dtype(series.dtype):
        return datetime_summary(series)
    if inferred == "boolean" or set(series.dropna().astype(str).str.casefold().unique()) <= {"true", "false", "yes", "no", "0", "1"}:
        return boolean_summary(series)
    return categorical_summary(series)


def summarize_all(data: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Return univariate summaries for all columns."""
    return {str(col): summarize_column(data[col]) for col in data.columns}
