"""Data-type detection and safe conversion."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from src.cleaning.audit import CleaningRecord

_DATE_TOKENS = ("date", "time", "timestamp", "dt", "year", "month", "day")


def detect_column_types(data: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """Infer the likely semantic type of each column.

    Returns per-column: inferred_type, confidence, is_identifier_candidate,
    is_numeric_string, is_date_string, current_dtype, n_unique, n_missing.
    """
    report: dict[str, dict[str, Any]] = {}
    n_rows = len(data)

    for col in data.columns:
        series = data[col]
        col_str = str(col)
        dtype_str = str(series.dtype)
        n_missing = int(series.isna().sum())
        n_unique = int(series.nunique(dropna=True))
        non_null = series.dropna()

        inferred = "unknown"
        confidence = 0.0

        if is_numeric_dtype(series.dtype):
            inferred = "numeric"
            confidence = 1.0
        elif is_datetime64_any_dtype(series.dtype):
            inferred = "datetime"
            confidence = 1.0
        elif non_null.empty:
            inferred = "empty"
            confidence = 1.0
        else:
            sample = non_null.astype(str).head(500)
            converted = pd.to_numeric(sample, errors="coerce")
            numeric_rate = converted.notna().mean()
            if numeric_rate >= 0.8:
                inferred = "numeric_string"
                confidence = round(numeric_rate, 2)
            else:
                parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
                date_rate = parsed.notna().mean()
                name_hint = any(tok in col_str.casefold() for tok in _DATE_TOKENS)
                if date_rate >= 0.9 and (name_hint or parsed.nunique() > 1):
                    inferred = "date_string"
                    confidence = round(date_rate, 2)
                else:
                    inferred = "categorical"
                    # confidence based on cardinality
                    cardinality = n_unique / max(n_rows - n_missing, 1)
                    confidence = round(1.0 - min(cardinality, 1.0), 2)

        is_identifier = any(
            hint in col_str.casefold() for hint in {"id", "identifier", "key", "code", "uid", "uuid"}
        ) or (n_rows > 0 and n_unique == n_rows - n_missing and n_missing == 0)

        report[col_str] = {
            "inferred_type": inferred,
            "confidence": confidence,
            "current_dtype": dtype_str,
            "n_unique": n_unique,
            "n_missing": n_missing,
            "is_identifier_candidate": is_identifier,
            "is_numeric_string": inferred == "numeric_string",
            "is_date_string": inferred == "date_string",
        }

    return report


def convert_types(
    data: pd.DataFrame,
    conversions: dict[str, str],
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Safely convert columns to target types.

    conversions maps column -> target_type ("numeric", "integer", "datetime",
    "categorical", "string", "boolean").
    Returns (cleaned_copy, records). Source is never mutated.  Invalid values
    are counted and disclosed, never silently dropped.
    """
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []

    for column, target in conversions.items():
        if column not in cleaned.columns:
            records.append(CleaningRecord(
                step="Fix types",
                column=column,
                operation=f"convert_to_{target}",
                rows_affected=0,
                parameters={"target_type": target},
                succeeded=False,
                warning=f"Column '{column}' not found.",
            ))
            continue

        series = cleaned[column]
        before_stats = {
            "dtype": str(series.dtype),
            "n_missing": int(series.isna().sum()),
            "n_unique": int(series.nunique(dropna=True)),
        }

        try:
            n_invalid = 0
            if target == "numeric":
                converted = pd.to_numeric(series, errors="coerce")
                n_invalid = int((series.notna() & converted.isna()).sum())
                cleaned[column] = converted
            elif target == "integer":
                converted = pd.to_numeric(series, errors="coerce")
                n_invalid = int((series.notna() & converted.isna()).sum())
                # Only convert to Int64 if no fractional values among valid
                valid = converted.dropna()
                if not valid.empty and (valid % 1 == 0).all():
                    cleaned[column] = converted.round().astype("Int64")
                else:
                    cleaned[column] = converted
            elif target == "datetime":
                converted = pd.to_datetime(series, errors="coerce", format="mixed")
                n_invalid = int((series.notna() & converted.isna()).sum())
                cleaned[column] = converted
            elif target == "categorical":
                cleaned[column] = series.astype("category")
                n_invalid = 0
            elif target == "string":
                cleaned[column] = series.astype("string")
                n_invalid = 0
            elif target == "boolean":
                truthy = {"true", "yes", "1", "t", "y"}
                falsy = {"false", "no", "0", "f", "n"}
                lowered = series.astype(str).str.strip().str.casefold()
                converted = lowered.map(
                    lambda v: True if v in truthy else (False if v in falsy else pd.NA)
                )
                n_invalid = int((series.notna() & converted.isna()).sum())
                cleaned[column] = converted
            else:
                raise ValueError(f"Unknown target type: {target}")

            after_stats = {
                "dtype": str(cleaned[column].dtype),
                "n_missing": int(cleaned[column].isna().sum()),
                "n_unique": int(cleaned[column].nunique(dropna=True)),
                "n_invalid_converted": n_invalid,
            }

            records.append(CleaningRecord(
                step="Fix types",
                column=column,
                operation=f"convert_to_{target}",
                rows_affected=int((series.astype(str) != cleaned[column].astype(str)).sum()),
                parameters={"target_type": target, "n_invalid": n_invalid},
                before_stats=before_stats,
                after_stats=after_stats,
                succeeded=True,
                warning=(
                    f"{n_invalid} value(s) could not be converted and became missing."
                    if n_invalid > 0 else None
                ),
            ))
        except Exception as error:  # noqa: BLE001
            records.append(CleaningRecord(
                step="Fix types",
                column=column,
                operation=f"convert_to_{target}",
                rows_affected=0,
                parameters={"target_type": target},
                before_stats=before_stats,
                after_stats={},
                succeeded=False,
                warning=str(error),
            ))

    return cleaned, records


def preserve_leading_zeros(
    data: pd.DataFrame,
    columns: list[str],
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Ensure identifier-like columns remain as strings to preserve leading zeros."""
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []

    for column in columns:
        if column not in cleaned.columns:
            continue
        if is_numeric_dtype(cleaned[column].dtype):
            cleaned[column] = cleaned[column].astype("string")
            records.append(CleaningRecord(
                step="Preserve leading zeros",
                column=column,
                operation="convert_to_string",
                rows_affected=len(cleaned),
                parameters={"reason": "identifier-like column"},
                succeeded=True,
            ))

    return cleaned, records
