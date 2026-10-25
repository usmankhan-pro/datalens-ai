"""Multivariate analysis: correlation matrix, pivots, grouped summaries."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype


def correlation_matrix(
    data: pd.DataFrame,
    method: str = "pearson",
    include_columns: list[str] | None = None,
    min_samples: int = 3,
) -> dict[str, Any]:
    """Compute a correlation matrix for numeric columns.

    Returns the matrix, a list of significant pairs, and metadata.
    """
    if include_columns is None:
        numeric_cols = data.select_dtypes(include="number").columns.tolist()
    else:
        numeric_cols = [c for c in include_columns if c in data.columns and is_numeric_dtype(data[c])]

    if len(numeric_cols) < 2:
        return {
            "method": method,
            "columns": numeric_cols,
            "matrix": {},
            "pairs": [],
            "n_pairs": 0,
            "note": "Need at least two numeric columns.",
        }

    matrix = data[numeric_cols].corr(method=method, numeric_only=True)

    # Extract pairs with |r| above a small threshold, excluding self-correlations
    pairs: list[dict[str, Any]] = []
    for i in range(len(numeric_cols)):
        for j in range(i + 1, len(numeric_cols)):
            col_a = numeric_cols[i]
            col_b = numeric_cols[j]
            val = float(matrix.loc[col_a, col_b]) if pd.notna(matrix.loc[col_a, col_b]) else None
            if val is None:
                continue
            n_valid = int(data[[col_a, col_b]].dropna().shape[0])
            if n_valid < min_samples:
                continue
            pairs.append({
                "column_a": col_a,
                "column_b": col_b,
                "correlation": round(val, 4),
                "abs_correlation": round(abs(val), 4),
                "n_samples": n_valid,
                "strength": _correlation_strength(abs(val)),
            })

    pairs.sort(key=lambda p: p["abs_correlation"], reverse=True)

    return {
        "method": method,
        "columns": numeric_cols,
        "matrix": matrix.round(4).to_dict(),
        "pairs": pairs,
        "n_pairs": len(pairs),
        "note": "Correlation does not imply causation. Interpret with caution on small samples.",
    }


def _correlation_strength(abs_r: float) -> str:
    if abs_r >= 0.8:
        return "very strong"
    if abs_r >= 0.6:
        return "strong"
    if abs_r >= 0.4:
        return "moderate"
    if abs_r >= 0.2:
        return "weak"
    return "very weak"


def pivot_table(
    data: pd.DataFrame,
    index: str,
    columns: str,
    values: str,
    aggfunc: str = "mean",
) -> dict[str, Any]:
    """Create a pivot table summary."""
    try:
        pv = data.pivot_table(
            index=index,
            columns=columns,
            values=values,
            aggfunc=aggfunc,
        )
        return {
            "index": index,
            "columns": columns,
            "values": values,
            "aggfunc": aggfunc,
            "table": pv.round(4).to_dict(),
            "shape": pv.shape,
        }
    except Exception as error:  # noqa: BLE001
        return {
            "error": str(error),
            "index": index,
            "columns": columns,
            "values": values,
            "aggfunc": aggfunc,
        }


def grouped_summary(
    data: pd.DataFrame,
    group_by: str,
    target: str,
    aggfuncs: list[str] | None = None,
) -> dict[str, Any]:
    """Grouped summary of a target column by a grouping column."""
    if aggfuncs is None:
        aggfuncs = ["count", "mean", "min", "max", "std"]
    try:
        grouped = data.groupby(group_by)[target].agg(aggfuncs)
        return {
            "group_by": group_by,
            "target": target,
            "aggfuncs": aggfuncs,
            "table": grouped.round(4).to_dict(),
            "n_groups": int(grouped.shape[0]),
        }
    except Exception as error:  # noqa: BLE001
        return {"error": str(error), "group_by": group_by, "target": target}


def multivariate_overview(data: pd.DataFrame) -> dict[str, Any]:
    """Summary of multivariate analysis opportunities."""
    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    categorical_cols = data.select_dtypes(include=["object", "string", "category"]).columns.tolist()
    n_rows = len(data)

    return {
        "n_rows": n_rows,
        "n_numeric": len(numeric_cols),
        "n_categorical": len(categorical_cols),
        "correlation_pairs_possible": len(numeric_cols) * (len(numeric_cols) - 1) // 2,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "can_compute_correlation": len(numeric_cols) >= 2 and n_rows >= 3,
    }
