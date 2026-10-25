"""Chart-selection logic: recommends visualizations based on column types, cardinality, and sample size."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


def column_kind(series: pd.Series) -> str:
    """Classify a series as numeric, datetime, or categorical."""
    if is_datetime64_any_dtype(series.dtype):
        return "datetime"
    if is_numeric_dtype(series.dtype):
        return "numeric"
    return "categorical"


def recommend_charts(
    data: pd.DataFrame,
    columns: list[str] | None = None,
    max_categorical_cardinality: int = 50,
) -> dict[str, list[dict[str, Any]]]:
    """Recommend charts for one or more columns.

    Returns a dict mapping column name -> list of chart recommendations,
    each with: chart_type, reason, suitable_for.
    """
    if columns is None:
        columns = list(data.columns)

    recommendations: dict[str, list[dict[str, Any]]] = {}

    for col in columns:
        if col not in data.columns:
            continue
        series = data[col]
        kind = column_kind(series)
        n_rows = len(series)
        n_missing = int(series.isna().sum())
        n_unique = int(series.nunique(dropna=True))
        cardinality_ratio = n_unique / max(n_rows - n_missing, 1)

        recs: list[dict[str, Any]] = []

        if kind == "numeric":
            recs.append({
                "chart_type": "histogram",
                "reason": "Distribution of numeric values",
                "suitable_for": "Univariate numeric analysis",
            })
            recs.append({
                "chart_type": "box_plot",
                "reason": "Outlier and quartile view",
                "suitable_for": "Univariate numeric analysis",
            })
            if cardinality_ratio <= 0.5 and n_unique <= max_categorical_cardinality:
                recs.append({
                    "chart_type": "bar_chart",
                    "reason": "Value frequency for low-cardinality numeric",
                    "suitable_for": "Categorical-like numeric inspection",
                })

        elif kind == "categorical":
            if n_unique <= max_categorical_cardinality:
                recs.append({
                    "chart_type": "bar_chart",
                    "reason": "Category frequency distribution",
                    "suitable_for": "Univariate categorical analysis",
                })
            else:
                recs.append({
                    "chart_type": "bar_chart",
                    "reason": f"Top categories (cardinality {n_unique} exceeds {max_categorical_cardinality})",
                    "suitable_for": "High-cardinality categorical inspection",
                })

        elif kind == "datetime":
            recs.append({
                "chart_type": "line_chart",
                "reason": "Temporal trend",
                "suitable_for": "Date/time series",
            })

        recommendations[col] = recs

    return recommendations


def recommend_pair_chart(
    data: pd.DataFrame,
    col_a: str,
    col_b: str,
) -> list[dict[str, Any]]:
    """Recommend chart types for a pair of columns based on their types."""
    kind_a = column_kind(data[col_a])
    kind_b = column_kind(data[col_b])

    recs: list[dict[str, Any]] = []

    if kind_a == "numeric" and kind_b == "numeric":
        recs.append({
            "chart_type": "scatter_plot",
            "reason": "Two numeric variables: relationship and correlation",
            "x": col_a,
            "y": col_b,
        })
        recs.append({
            "chart_type": "line_chart",
            "reason": "Two numeric variables: trend over ordered X",
            "x": col_a,
            "y": col_b,
        })
    elif {kind_a, kind_b} == {"numeric", "categorical"}:
        cat = col_a if kind_a == "categorical" else col_b
        num = col_b if kind_a == "categorical" else col_a
        recs.append({
            "chart_type": "box_plot",
            "reason": "Numeric vs categorical: compare distributions",
            "x": cat,
            "y": num,
            "category_column": cat,
        })
    elif kind_a == "datetime" and kind_b == "numeric":
        recs.append({
            "chart_type": "line_chart",
            "reason": "Date vs numeric: time series",
            "x": col_a,
            "y": col_b,
        })
    elif kind_a == "numeric" and kind_b == "datetime":
        recs.append({
            "chart_type": "line_chart",
            "reason": "Numeric vs date: time series",
            "x": col_b,
            "y": col_a,
        })
    elif kind_a == "categorical" and kind_b == "categorical":
        recs.append({
            "chart_type": "bar_chart",
            "reason": "Categorical vs categorical: grouped counts",
            "x": col_a,
            "y": col_b,
        })
    elif "datetime" in {kind_a, kind_b} and "categorical" in {kind_a, kind_b}:
        date_col = col_a if kind_a == "datetime" else col_b
        cat_col = col_b if kind_a == "datetime" else col_a
        recs.append({
            "chart_type": "line_chart",
            "reason": "Category counts over time",
            "x": date_col,
            "category_column": cat_col,
        })

    return recs


def recommend_correlation_chart(
    data: pd.DataFrame,
    columns: list[str] | None = None,
) -> dict[str, Any]:
    """Recommend whether a correlation heatmap is appropriate."""
    if columns is None:
        columns = data.select_dtypes(include="number").columns.tolist()

    numeric_cols = [c for c in columns if c in data.columns and is_numeric_dtype(data[c])]

    if len(numeric_cols) < 2:
        return {
            "recommended": False,
            "reason": "Need at least two numeric columns for a correlation matrix.",
            "columns": numeric_cols,
        }

    n_rows = len(data)
    if n_rows < 3:
        return {
            "recommended": False,
            "reason": "Too few rows for reliable correlation.",
            "columns": numeric_cols,
        }

    return {
        "recommended": True,
        "reason": f"{len(numeric_cols)} numeric columns available for correlation analysis.",
        "columns": numeric_cols,
        "n_pairs": len(numeric_cols) * (len(numeric_cols) - 1) // 2,
    }
