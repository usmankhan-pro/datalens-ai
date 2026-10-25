"""User-configured, deterministic column validation rules."""

from __future__ import annotations

from typing import Any

import pandas as pd


def evaluate_range_rule(
    data: pd.DataFrame,
    column: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> dict[str, Any]:
    """Count non-missing numeric values outside inclusive bounds."""
    if column not in data.columns:
        raise ValueError(f"Column '{column}' does not exist.")
    if not pd.api.types.is_numeric_dtype(data[column]):
        raise ValueError(f"Column '{column}' must be numeric for a range rule.")
    if minimum is None and maximum is None:
        raise ValueError("Provide at least one bound for a range rule.")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError("Minimum cannot exceed maximum.")

    values = data[column]
    invalid = pd.Series(False, index=values.index)
    if minimum is not None:
        invalid |= values < minimum
    if maximum is not None:
        invalid |= values > maximum
    invalid &= values.notna()
    return {
        "column": column,
        "rule": "range",
        "checked": int(values.notna().sum()),
        "invalid": int(invalid.sum()),
        "invalid_indices": data.index[invalid].tolist(),
        "minimum": minimum,
        "maximum": maximum,
    }


def evaluate_allowed_values_rule(
    data: pd.DataFrame,
    column: str,
    allowed_values: list[str],
) -> dict[str, Any]:
    """Count non-missing values that are not in a configured allow-list."""
    if column not in data.columns:
        raise ValueError(f"Column '{column}' does not exist.")
    normalized = [value.strip() for value in allowed_values if value.strip()]
    if not normalized:
        raise ValueError("Provide at least one allowed value.")

    values = data[column]
    invalid = values.notna() & ~values.astype(str).isin(normalized)
    return {
        "column": column,
        "rule": "allowed_values",
        "checked": int(values.notna().sum()),
        "invalid": int(invalid.sum()),
        "invalid_indices": data.index[invalid].tolist(),
        "allowed_values": normalized,
    }
