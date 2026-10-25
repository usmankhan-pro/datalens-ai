"""Issue detection engine for data-quality findings.

Produces structured findings (severity, column, title, detail, suggestion)
from a DataFrame, optionally reusing precomputed column profiles.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

from config.settings import (
    CARDINALITY_THRESHOLDS,
    DUPLICATE_THRESHOLDS,
    IDENTIFIER_NAME_HINTS,
    MISSING_THRESHOLDS,
)

_DATE_TOKENS = ("date", "time", "timestamp", "dt", "year", "month", "day")
_TEXT_DTYPES = frozenset(("object", "string", "str"))

_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}

Finding = dict[str, str]


def _finding(
    severity: str,
    column: str,
    title: str,
    detail: str,
    suggestion: str,
) -> Finding:
    return {
        "severity": severity,
        "column": column,
        "title": title,
        "detail": detail,
        "suggestion": suggestion,
    }


def _is_text_dtype(dtype_str: str) -> bool:
    return dtype_str in _TEXT_DTYPES or dtype_str.startswith("string")


def _is_likely_date_column(series: pd.Series) -> bool:
    if is_datetime64_any_dtype(series.dtype):
        return False
    values = series.dropna()
    if values.empty:
        return False
    sample = values.astype(str).head(500)
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    name_hint = any(tok in str(series.name).casefold() for tok in _DATE_TOKENS)
    parse_rate = parsed.notna().mean()
    return parse_rate >= 0.9 and (name_hint or parsed.nunique() > 1)


def _is_numeric_string_column(series: pd.Series) -> bool:
    if is_numeric_dtype(series.dtype) or is_datetime64_any_dtype(series.dtype):
        return False
    values = series.dropna()
    if values.empty:
        return False
    sample = values.astype(str).head(500)
    converted = pd.to_numeric(sample, errors="coerce")
    return converted.notna().mean() >= 0.8


def _profile_column(series: pd.Series, n_rows: int) -> dict[str, Any]:
    n_missing = int(series.isna().sum())
    missing_pct = round(n_missing / n_rows * 100, 2) if n_rows > 0 else 0.0
    n_unique = int(series.nunique(dropna=True))
    dtype_str = str(series.dtype)
    non_null = series.dropna()

    return {
        "dtype": dtype_str,
        "n_missing": n_missing,
        "missing_pct": missing_pct,
        "n_unique": n_unique,
        "is_all_null": series.isna().all(),
        "is_constant": n_unique == 1 and not series.isna().all(),
        "is_numeric_string": _is_numeric_string_column(series)
        if not non_null.empty and not is_numeric_dtype(series.dtype)
        and not is_datetime64_any_dtype(series.dtype)
        else False,
        "is_date_string": _is_likely_date_column(series)
        if not non_null.empty and not is_datetime64_any_dtype(series.dtype)
        else False,
        "std": None,
    }


def detect_issues(
    data: pd.DataFrame,
    col_profiles: dict[str, dict[str, Any]] | None = None,
) -> list[Finding]:
    """Return a prioritized list of data-quality findings.

    Each finding is a dict with keys: severity, column, title, detail, suggestion.
    Findings are sorted HIGH -> INFO, then alphabetically by column.
    """
    if col_profiles is None:
        n_rows = len(data)
        col_profiles = {
            str(col): _profile_column(data.iloc[:, pos], n_rows)
            for pos, col in enumerate(data.columns)
        }

    findings: list[Finding] = []
    n_rows = len(data)

    # ---- Dataset-level findings ----
    if n_rows == 0:
        findings.append(_finding(
            "HIGH", "Dataset", "Empty dataset",
            "The dataset contains no rows.",
            "Verify the upload source or file format.",
        ))
        return _sorted(findings)

    n_duplicates = int(data.duplicated().sum())
    if n_duplicates > 0:
        pct = round(n_duplicates / n_rows * 100, 1)
        severity = "HIGH" if pct > DUPLICATE_THRESHOLDS.high else "MEDIUM"
        findings.append(_finding(
            severity, "Dataset", "Duplicate rows",
            f"{n_duplicates:,} exact duplicate rows ({pct}% of dataset).",
            "Consider removing duplicates in the Cleaning Studio.",
        ))

    n_empty_rows = int(data.isna().all(axis=1).sum())
    if n_empty_rows > 0:
        findings.append(_finding(
            "MEDIUM", "Dataset", "Completely empty rows",
            f"{n_empty_rows:,} rows have no values in any column.",
            "Drop these rows; they carry no information.",
        ))

    seen: set[str] = set()
    dup_names: list[str] = []
    for col in data.columns:
        col_str = str(col)
        if col_str in seen:
            dup_names.append(col_str)
        seen.add(col_str)
    if dup_names:
        findings.append(_finding(
            "HIGH", "Dataset", "Duplicate column names",
            f"Column name(s) appear more than once: {', '.join(dup_names)}.",
            "Rename columns to be unique before analysis.",
        ))

    # ---- Per-column findings ----
    for col in col_profiles:
        p = col_profiles[col]

        if p["is_all_null"]:
            findings.append(_finding(
                "HIGH", col, "Column is entirely empty",
                f"'{col}' has no non-null values.",
                "Drop this column or verify the data source.",
            ))
            continue

        if p["is_constant"]:
            findings.append(_finding(
                "LOW", col, "Constant column",
                f"'{col}' contains only one distinct value across all rows.",
                "This column carries no discriminating information; consider dropping it.",
            ))

        if p["n_missing"] > 0:
            pct = p["missing_pct"]
            if pct >= MISSING_THRESHOLDS.high:
                severity = "HIGH"
            elif pct >= MISSING_THRESHOLDS.medium:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            findings.append(_finding(
                severity, col, "Missing values",
                f"'{col}' has {p['n_missing']:,} missing values ({pct:.1f}%).",
                "Choose an imputation strategy or drop rows in the Cleaning Studio.",
            ))

        if p["is_numeric_string"]:
            findings.append(_finding(
                "MEDIUM", col, "Numeric values stored as text",
                f"'{col}' is stored as {p['dtype']} but most non-null values parse as numbers.",
                "Use 'Fix types' in the Cleaning Studio to convert to numeric.",
            ))

        if p["is_date_string"]:
            findings.append(_finding(
                "LOW", col, "Date-like values stored as text",
                f"'{col}' is stored as {p['dtype']} but values appear to be dates.",
                "Parse this column as datetime to enable time-series analysis.",
            ))

        if (
            _is_text_dtype(str(p["dtype"]))
            and not p["is_numeric_string"]
            and not p["is_date_string"]
            and n_rows > CARDINALITY_THRESHOLDS.min_rows
            and p["n_unique"] >= CARDINALITY_THRESHOLDS.ratio * (n_rows - p["n_missing"])
            and p["n_unique"] > CARDINALITY_THRESHOLDS.min_unique
        ):
            findings.append(_finding(
                "INFO", col, "High cardinality text column",
                f"'{col}' has {p['n_unique']:,} unique values "
                f"({p['n_unique'] / max(n_rows - p['n_missing'], 1):.0%} of non-null rows).",
                "This may be a free-text or ID column. Aggregation may not be meaningful.",
            ))

    return _sorted(findings)


def _sorted(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (_SEVERITY_ORDER.get(f["severity"], 99), f["column"]),
    )


def rank_by_importance(findings: list[Finding]) -> list[Finding]:
    """Re-sort findings by severity then by practical importance.

    HIGH-severity findings affecting the dataset come first, followed by
    per-column findings ordered by severity and then by missing/duplicate count.
    """
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    dataset_first = sorted(
        findings,
        key=lambda f: (
            0 if f["column"] == "Dataset" else 1,
            severity_order.get(f["severity"], 99),
            f["column"],
        ),
    )
    return dataset_first
