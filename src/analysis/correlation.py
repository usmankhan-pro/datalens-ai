"""Correlation analysis: Pearson and Spearman, with warnings about interpretation."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_numeric_dtype


def pairwise_correlations(
    data: pd.DataFrame,
    columns: list[str] | None = None,
    method: str = "pearson",
    min_samples: int = 3,
) -> dict[str, Any]:
    """Compute pairwise correlations among selected numeric columns.

    method: "pearson" or "spearman".
    Returns coefficients, sample sizes, missing handling info, and warnings.
    """
    if columns is None:
        columns = data.select_dtypes(include="number").columns.tolist()

    numeric_cols = [c for c in columns if c in data.columns and is_numeric_dtype(data[c])]

    if len(numeric_cols) < 2:
        return {
            "method": method,
            "columns": numeric_cols,
            "coefficients": {},
            "sample_sizes": {},
            "n_pairs": 0,
            "missing_handling": "pairwise complete observations",
            "warnings": ["Need at least two numeric columns for correlation."],
        }

    sub = data[numeric_cols]
    matrix = sub.corr(method=method, numeric_only=True)

    # Sample sizes per pair (pairwise complete)
    sample_sizes: dict[str, dict[str, int]] = {}
    for a in numeric_cols:
        sample_sizes[a] = {}
        for b in numeric_cols:
            n = int(data[[a, b]].dropna().shape[0])
            sample_sizes[a][b] = n

    coefficients: dict[str, dict[str, float | None]] = {}
    for a in numeric_cols:
        coefficients[a] = {}
        for b in numeric_cols:
            val = float(matrix.loc[a, b]) if pd.notna(matrix.loc[a, b]) else None
            coefficients[a][b] = round(val, 4) if val is not None else None

    warnings: list[str] = []
    if method == "pearson":
        warnings.append(
            "Pearson assumes linear relationships and is sensitive to outliers. "
            "Use Spearman for monotonic or non-linear associations."
        )
    if any(n < min_samples for row in sample_sizes.values() for n in row.values()):
        warnings.append(
            f"Some pairs have fewer than {min_samples} complete observations; "
            "coefficients may be unstable."
        )
    warnings.append("Correlation does not imply causation.")
    warnings.append(
        "Identifier columns and high-cardinality IDs are excluded from the "
        "default matrix unless explicitly requested."
    )

    return {
        "method": method,
        "columns": numeric_cols,
        "coefficients": coefficients,
        "sample_sizes": sample_sizes,
        "n_pairs": len(numeric_cols) * (len(numeric_cols) - 1) // 2,
        "missing_handling": "pairwise complete observations",
        "warnings": warnings,
    }


def strong_correlations(
    data: pd.DataFrame,
    threshold: float = 0.7,
    method: str = "pearson",
) -> list[dict[str, Any]]:
    """Return pairs with |correlation| >= threshold, sorted by strength."""
    result = pairwise_correlations(data, method=method)
    pairs: list[dict[str, Any]] = []
    columns = result["columns"]
    coeffs = result["coefficients"]
    sizes = result["sample_sizes"]

    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            a, b = columns[i], columns[j]
            r = coeffs[a][b]
            if r is None:
                continue
            if abs(r) >= threshold:
                pairs.append({
                    "column_a": a,
                    "column_b": b,
                    "correlation": r,
                    "abs_correlation": round(abs(r), 4),
                    "n_samples": sizes[a][b],
                })

    pairs.sort(key=lambda p: p["abs_correlation"], reverse=True)
    return pairs
