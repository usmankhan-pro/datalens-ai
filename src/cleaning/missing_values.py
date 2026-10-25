"""Missing-value cleaning strategies."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.cleaning.audit import CleaningRecord

_PLACEHOLDERS = frozenset(
    {"n/a", "na", "null", "none", "nan", "unknown", "missing", "-", "--", ""}
)


def _normalize_placeholders(series: pd.Series) -> pd.Series:
    """Treat configured placeholder strings as missing in object columns."""
    if series.dtype == object or str(series.dtype).startswith("string"):
        return series.replace(list(_PLACEHOLDERS), pd.NA)
    return series


def detect_missing(
    data: pd.DataFrame,
    include_placeholders: bool = True,
) -> dict[str, dict[str, Any]]:
    """Return per-column missing-value statistics.

    Keys: n_missing, missing_pct, n_placeholder, total_rows.
    """
    report: dict[str, dict[str, Any]] = {}
    n_rows = len(data)
    for col in data.columns:
        series = data[col]
        working = _normalize_placeholders(series) if include_placeholders else series
        n_missing = int(working.isna().sum())
        n_placeholder = 0
        if include_placeholders and series.dtype == object:
            n_placeholder = int(
                series.astype(str).str.strip().str.casefold().isin(_PLACEHOLDERS).sum()
            )
        report[str(col)] = {
            "n_missing": n_missing,
            "missing_pct": round(n_missing / n_rows * 100, 2) if n_rows > 0 else 0.0,
            "n_placeholder": n_placeholder,
            "total_rows": n_rows,
            "dtype": str(series.dtype),
        }
    return report


def fill_missing(
    data: pd.DataFrame,
    rules: dict[str, tuple[str, str]],
    include_placeholders: bool = True,
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Apply configured missing-value rules to a copy.

    rules maps column -> (method, custom_value).
    Supported methods: "Drop rows", "Mean", "Median", "Mode", "Custom".
    Returns (cleaned_copy, records).  Source is never mutated.
    """
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []

    for column, (method, custom) in rules.items():
        if column not in cleaned.columns:
            records.append(CleaningRecord(
                step="Missing values",
                column=column,
                operation=method,
                rows_affected=0,
                parameters={"method": method, "custom": custom},
                succeeded=False,
                warning=f"Column '{column}' not found.",
            ))
            continue

        series = cleaned[column]
        working = _normalize_placeholders(series) if include_placeholders else series
        missing_mask = working.isna()
        n_missing = int(missing_mask.sum())

        if n_missing == 0:
            continue

        before_stats = {
            "n_missing": n_missing,
            "missing_pct": round(n_missing / len(cleaned) * 100, 2),
            "dtype": str(series.dtype),
        }

        try:
            if method == "Drop rows":
                cleaned = cleaned.loc[~missing_mask].copy()
                rows_affected = n_missing
            elif method == "Mean":
                if not pd.api.types.is_numeric_dtype(working):
                    raise ValueError(f"Column '{column}' is not numeric; cannot use Mean.")
                fill_value = float(working.mean())
                cleaned[column] = working.fillna(fill_value)
                rows_affected = n_missing
            elif method == "Median":
                if not pd.api.types.is_numeric_dtype(working):
                    raise ValueError(f"Column '{column}' is not numeric; cannot use Median.")
                fill_value = float(working.median())
                cleaned[column] = working.fillna(fill_value)
                rows_affected = n_missing
            elif method == "Mode":
                mode_values = working.mode()
                if mode_values.empty:
                    raise ValueError(f"Column '{column}' has no mode to impute.")
                fill_value = mode_values.iloc[0]
                cleaned[column] = working.fillna(fill_value)
                rows_affected = n_missing
            elif method == "Custom":
                cleaned[column] = working.fillna(custom)
                rows_affected = n_missing
            else:
                raise ValueError(f"Unknown missing-value method: {method}")

            after_stats = {
                "n_missing": int(cleaned[column].isna().sum()) if column in cleaned.columns else 0,
                "missing_pct": 0.0,
            }

            records.append(CleaningRecord(
                step=f"Missing values: {method}",
                column=column,
                operation=method,
                rows_affected=rows_affected,
                parameters={"method": method, "custom": custom},
                before_stats=before_stats,
                after_stats=after_stats,
                succeeded=True,
            ))
        except Exception as error:  # noqa: BLE001 - surface validation warning, continue
            records.append(CleaningRecord(
                step=f"Missing values: {method}",
                column=column,
                operation=method,
                rows_affected=0,
                parameters={"method": method, "custom": custom},
                before_stats=before_stats,
                after_stats={},
                succeeded=False,
                warning=str(error),
            ))

    return cleaned, records


def add_missingness_indicators(
    data: pd.DataFrame,
    columns: list[str] | None = None,
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Add boolean indicator columns for missingness in selected columns."""
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []
    targets = columns or [
        str(col) for col in data.columns if data[col].isna().any()
    ]
    for column in targets:
        if column not in cleaned.columns:
            continue
        indicator_name = f"{column}_is_missing"
        cleaned[indicator_name] = cleaned[column].isna()
        n_indicated = int(cleaned[indicator_name].sum())
        records.append(CleaningRecord(
            step="Missingness indicator",
            column=column,
            operation="add_indicator",
            rows_affected=n_indicated,
            parameters={"indicator_column": indicator_name},
            succeeded=True,
        ))
    return cleaned, records
