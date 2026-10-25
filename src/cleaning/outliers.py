"""Outlier detection and handling using IQR and Z-score methods."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.cleaning.audit import CleaningRecord


def detect_outliers_iqr(
    data: pd.DataFrame,
    column: str,
    multiplier: float = 1.5,
) -> dict[str, Any]:
    """Detect IQR-based outliers in one numeric column.

    Returns indices, count, fences, and the outlier values.
    """
    values = data[column].dropna()
    if values.empty:
        return {
            "column": column,
            "n_outliers": 0,
            "outlier_indices": [],
            "lower_fence": None,
            "upper_fence": None,
            "q1": None,
            "q3": None,
            "iqr": None,
            "outlier_values": [],
        }

    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower_fence = q1 - multiplier * iqr
    upper_fence = q3 + multiplier * iqr

    outlier_mask = (data[column] < lower_fence) | (data[column] > upper_fence)
    outlier_indices = data.index[outlier_mask].tolist()
    outlier_values = data.loc[outlier_indices, column].tolist()

    return {
        "column": column,
        "n_outliers": int(outlier_mask.sum()),
        "outlier_indices": outlier_indices,
        "lower_fence": lower_fence,
        "upper_fence": upper_fence,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "outlier_values": outlier_values,
    }


def detect_outliers_zscore(
    data: pd.DataFrame,
    column: str,
    threshold: float = 3.0,
) -> dict[str, Any]:
    """Detect Z-score-based outliers in one numeric column."""
    values = data[column].dropna()
    if values.empty or values.std() == 0:
        return {
            "column": column,
            "n_outliers": 0,
            "outlier_indices": [],
            "threshold": threshold,
            "mean": None,
            "std": None,
            "outlier_values": [],
        }

    mean = float(values.mean())
    std = float(values.std())
    z_scores = (data[column] - mean) / std
    outlier_mask = z_scores.abs() > threshold
    outlier_indices = data.index[outlier_mask].tolist()

    return {
        "column": column,
        "n_outliers": int(outlier_mask.sum()),
        "outlier_indices": outlier_indices,
        "threshold": threshold,
        "mean": mean,
        "std": std,
        "outlier_values": data.loc[outlier_indices, column].tolist(),
    }


def handle_outliers(
    data: pd.DataFrame,
    rules: dict[str, dict[str, Any]],
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Apply outlier actions to a copy.

    rules maps column -> {"method": "iqr"|"zscore", "action": "ignore"|"cap"|"remove"|"flag",
    "multiplier": float, "threshold": float}.

    Returns (cleaned_copy, records). Source is never mutated.
    """
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []

    for column, rule in rules.items():
        if column not in cleaned.columns:
            records.append(CleaningRecord(
                step="Outlier handling",
                column=column,
                operation=rule.get("action", "ignore"),
                rows_affected=0,
                parameters=rule,
                succeeded=False,
                warning=f"Column '{column}' not found.",
            ))
            continue

        action = rule.get("action", "ignore")
        method = rule.get("method", "iqr")

        if method == "zscore":
            detection = detect_outliers_zscore(cleaned, column, rule.get("threshold", 3.0))
        else:
            detection = detect_outliers_iqr(cleaned, column, rule.get("multiplier", 1.5))

        n_outliers = detection["n_outliers"]
        before_stats = {
            "n_outliers": n_outliers,
            "min": float(cleaned[column].min()) if pd.api.types.is_numeric_dtype(cleaned[column]) else None,
            "max": float(cleaned[column].max()) if pd.api.types.is_numeric_dtype(cleaned[column]) else None,
        }

        if action == "ignore" or n_outliers == 0:
            records.append(CleaningRecord(
                step="Outlier handling",
                column=column,
                operation=action,
                rows_affected=0,
                parameters=rule,
                before_stats=before_stats,
                after_stats=before_stats,
                succeeded=True,
            ))
            continue

        if action == "cap":
            if method == "iqr":
                low = detection["lower_fence"]
                high = detection["upper_fence"]
            else:
                mean = detection["mean"] or 0.0
                std = detection["std"] or 1.0
                thresh = rule.get("threshold", 3.0)
                low = mean - thresh * std
                high = mean + thresh * std
            cleaned[column] = cleaned[column].clip(lower=low, upper=high)
            rows_affected = n_outliers
        elif action == "remove":
            outlier_indices = set(detection["outlier_indices"])
            cleaned = cleaned.loc[~cleaned.index.isin(outlier_indices)].copy()
            rows_affected = n_outliers
        elif action == "flag":
            flag_col = f"{column}_is_outlier"
            cleaned[flag_col] = cleaned.index.isin(detection["outlier_indices"])
            rows_affected = n_outliers
        else:
            records.append(CleaningRecord(
                step="Outlier handling",
                column=column,
                operation=action,
                rows_affected=0,
                parameters=rule,
                before_stats=before_stats,
                after_stats={},
                succeeded=False,
                warning=f"Unknown outlier action: {action}",
            ))
            continue

        after_stats = {
            "n_outliers": 0,
            "min": float(cleaned[column].min()) if pd.api.types.is_numeric_dtype(cleaned[column]) else None,
            "max": float(cleaned[column].max()) if pd.api.types.is_numeric_dtype(cleaned[column]) else None,
            "n_rows": len(cleaned),
        }

        records.append(CleaningRecord(
            step="Outlier handling",
            column=column,
            operation=action,
            rows_affected=rows_affected,
            parameters=rule,
            before_stats=before_stats,
            after_stats=after_stats,
            succeeded=True,
        ))

    return cleaned, records
