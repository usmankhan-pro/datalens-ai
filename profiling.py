"""Dataset profiling and data-quality assessment.

All public functions accept a DataFrame and return plain Python structures
(dicts, lists, DataFrames).  No Streamlit imports.  Source data is never
mutated.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DATE_TOKENS = ("date", "time", "timestamp", "dt", "year", "month", "day")
_NUMERIC_STRING_SAMPLE = 500   # rows sampled to detect numeric strings
_DATE_STRING_SAMPLE = 500      # rows sampled to detect date-like strings
_TOP_CATEGORIES = 5            # how many top values to surface per cat column
_TEXT_DTYPES = frozenset(("object", "string", "str"))  # pd dtype name strings


def _is_text_dtype(dtype_str: str) -> bool:
    """Return True for any dtype that represents text/string data."""
    return dtype_str in _TEXT_DTYPES or dtype_str.startswith("string")


def _is_likely_date_column(series: pd.Series) -> bool:
    """Return True when a non-datetime object column looks like dates."""
    if is_datetime64_any_dtype(series.dtype):
        return False  # already typed – handled separately
    values = series.dropna()
    if values.empty:
        return False
    sample = values.astype(str).head(_DATE_STRING_SAMPLE)
    parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
    name_hint = any(tok in series.name.casefold() for tok in _DATE_TOKENS)
    parse_rate = parsed.notna().mean()
    return parse_rate >= 0.9 and (name_hint or parsed.nunique() > 1)


def _is_numeric_string_column(series: pd.Series) -> bool:
    """Return True when a non-numeric object column is mostly numeric values."""
    if is_numeric_dtype(series.dtype) or is_datetime64_any_dtype(series.dtype):
        return False
    values = series.dropna()
    if values.empty:
        return False
    sample = values.astype(str).head(_NUMERIC_STRING_SAMPLE)
    converted = pd.to_numeric(sample, errors="coerce")
    return converted.notna().mean() >= 0.8


def _safe_round(value: float | None, decimals: int = 4) -> float | None:
    """Round a float, returning None if the value is not finite."""
    if value is None or not np.isfinite(value):
        return None
    return round(float(value), decimals)


def _memory_label(bytes_: int) -> str:
    """Convert byte count to a human-readable label."""
    for unit in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}"
        bytes_ /= 1024  # type: ignore[assignment]
    return f"{bytes_:.1f} TB"


# ---------------------------------------------------------------------------
# Dataset-level profile
# ---------------------------------------------------------------------------

def profile_dataset(data: pd.DataFrame) -> dict[str, Any]:
    """Return structural and quality statistics for the whole dataset.

    The source DataFrame is not modified.

    Returns a dict with keys:
        n_rows, n_cols, memory_bytes, memory_label,
        n_duplicates, n_missing_cells, missing_pct,
        n_empty_rows, n_empty_cols, n_constant_cols,
        unique_per_column (dict col -> int),
        duplicate_column_names (list of str)
    """
    n_rows, n_cols = data.shape

    # Memory
    memory_bytes = int(data.memory_usage(index=True, deep=True).sum())

    # Duplicates (exact row matches)
    n_duplicates = int(data.duplicated().sum()) if n_rows > 0 else 0

    # Missing cells
    n_missing_cells = int(data.isna().sum().sum())
    total_cells = n_rows * n_cols
    missing_pct = round(n_missing_cells / total_cells * 100, 2) if total_cells > 0 else 0.0

    # Empty rows (every cell NA)
    n_empty_rows = int(data.isna().all(axis=1).sum()) if n_cols > 0 else 0

    # Empty and constant columns
    # Use positional indexing (iloc) to avoid DataFrame ambiguity when column
    # names are duplicated – data[col] would return a DataFrame in that case.
    n_empty_cols = 0
    n_constant_cols = 0
    unique_per_column: dict[str, int] = {}
    for pos, col in enumerate(data.columns):
        col_key = str(col)
        series = data.iloc[:, pos]
        unique_count = int(series.nunique(dropna=True))
        # For duplicate col names keep the last observed unique count
        unique_per_column[col_key] = unique_count
        if series.isna().all():
            n_empty_cols += 1
        elif unique_count <= 1 and n_rows > 0:
            if not series.isna().all():
                n_constant_cols += 1

    # Duplicate column names
    seen: set[str] = set()
    duplicate_column_names: list[str] = []
    for col in data.columns:
        col_str = str(col)
        if col_str in seen:
            duplicate_column_names.append(col_str)
        seen.add(col_str)

    return {
        "n_rows": n_rows,
        "n_cols": n_cols,
        "memory_bytes": memory_bytes,
        "memory_label": _memory_label(memory_bytes),
        "n_duplicates": n_duplicates,
        "n_missing_cells": n_missing_cells,
        "missing_pct": missing_pct,
        "n_empty_rows": n_empty_rows,
        "n_empty_cols": n_empty_cols,
        "n_constant_cols": n_constant_cols,
        "unique_per_column": unique_per_column,
        "duplicate_column_names": duplicate_column_names,
    }


# ---------------------------------------------------------------------------
# Column-level profile
# ---------------------------------------------------------------------------

def _profile_one_column(series: pd.Series, n_rows: int) -> dict[str, Any]:
    """Compute the full profile for one column."""
    n_missing = int(series.isna().sum())
    missing_pct = round(n_missing / n_rows * 100, 2) if n_rows > 0 else 0.0
    n_unique = int(series.nunique(dropna=True))
    dtype_str = str(series.dtype)
    non_null = series.dropna()

    profile: dict[str, Any] = {
        "dtype": dtype_str,
        "n_missing": n_missing,
        "missing_pct": missing_pct,
        "n_unique": n_unique,
        # numeric stats
        "min": None, "max": None, "mean": None,
        "median": None, "std": None, "q1": None, "q3": None,
        # categorical stats
        "top_categories": {},
        # date stats
        "date_min": None, "date_max": None,
        # flags
        "is_constant": False,
        "is_all_null": series.isna().all(),
        "is_numeric_string": False,
        "is_date_string": False,
    }

    # Constant check (ignoring nulls)
    if n_unique == 1 and not series.isna().all():
        profile["is_constant"] = True

    if non_null.empty:
        return profile

    # Numeric columns
    if is_numeric_dtype(series.dtype):
        try:
            numeric_vals = non_null.astype(float)
            profile["min"] = _safe_round(float(numeric_vals.min()))
            profile["max"] = _safe_round(float(numeric_vals.max()))
            profile["mean"] = _safe_round(float(numeric_vals.mean()))
            profile["median"] = _safe_round(float(numeric_vals.median()))
            profile["std"] = _safe_round(float(numeric_vals.std()))
            profile["q1"] = _safe_round(float(numeric_vals.quantile(0.25)))
            profile["q3"] = _safe_round(float(numeric_vals.quantile(0.75)))
        except (TypeError, ValueError):
            pass
        return profile

    # Datetime columns
    if is_datetime64_any_dtype(series.dtype):
        try:
            profile["date_min"] = str(non_null.min().date())
            profile["date_max"] = str(non_null.max().date())
        except (AttributeError, ValueError):
            pass
        return profile

    # Object / string / category columns
    top = series.value_counts(dropna=True).head(_TOP_CATEGORIES)
    profile["top_categories"] = {str(k): int(v) for k, v in top.items()}

    # Detect text columns storing numeric or date values
    profile["is_numeric_string"] = _is_numeric_string_column(series)
    if not profile["is_numeric_string"]:
        profile["is_date_string"] = _is_likely_date_column(series)

    return profile


def profile_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with one row per column and all quality metrics.

    Columns in the returned DataFrame:
        dtype, n_missing, missing_pct, n_unique,
        min, max, mean, median, std, q1, q3,
        top_categories (dict), date_min, date_max,
        is_constant, is_all_null, is_numeric_string, is_date_string
    """
    n_rows = len(data)
    rows = {}
    for pos, col in enumerate(data.columns):
        # Use positional access so duplicate column names don't cause ambiguity.
        rows[str(col)] = _profile_one_column(data.iloc[:, pos], n_rows)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame.from_dict(rows, orient="index")
    result.index.name = "column"
    return result


# ---------------------------------------------------------------------------
# Quality findings
# ---------------------------------------------------------------------------

_SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}

Finding = dict[str, str]  # keys: severity, column, title, detail, suggestion


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


def find_quality_findings(
    data: pd.DataFrame,
    col_profiles: pd.DataFrame | None = None,
) -> list[Finding]:
    """Return a prioritised list of data-quality findings.

    Each finding is a dict with keys:
        severity   - HIGH | MEDIUM | LOW | INFO
        column     - column name or "Dataset"
        title      - one-line problem label
        detail     - measured fact (no editorialising)
        suggestion - possible next action

    Findings are sorted HIGH -> INFO then alphabetically by column.
    """
    if col_profiles is None:
        col_profiles = profile_columns(data)

    findings: list[Finding] = []
    n_rows = len(data)

    # -- Dataset-level findings -----------------------------------------------

    ds = profile_dataset(data)

    if n_rows == 0:
        findings.append(_finding(
            "HIGH", "Dataset", "Empty dataset",
            "The dataset contains no rows.",
            "Verify the upload source or file format.",
        ))
        return findings  # nothing else is meaningful

    if ds["n_duplicates"] > 0:
        pct = round(ds["n_duplicates"] / n_rows * 100, 1)
        severity = "HIGH" if pct > 10 else "MEDIUM"
        findings.append(_finding(
            severity, "Dataset", "Duplicate rows",
            f"{ds['n_duplicates']:,} exact duplicate rows ({pct}% of dataset).",
            "Consider removing duplicates in the Cleaning tab.",
        ))

    if ds["n_empty_rows"] > 0:
        findings.append(_finding(
            "MEDIUM", "Dataset", "Completely empty rows",
            f"{ds['n_empty_rows']:,} rows have no values in any column.",
            "Drop these rows; they carry no information.",
        ))

    if ds["duplicate_column_names"]:
        names = ", ".join(ds["duplicate_column_names"])
        findings.append(_finding(
            "HIGH", "Dataset", "Duplicate column names",
            f"Column name(s) appear more than once: {names}.",
            "Rename columns to be unique before analysis.",
        ))

    # -- Per-column findings --------------------------------------------------

    if col_profiles.empty:
        return _sorted_findings(findings)

    for col in col_profiles.index:
        p = col_profiles.loc[col]

        # All-null column
        if p["is_all_null"]:
            findings.append(_finding(
                "HIGH", col, "Column is entirely empty",
                f"'{col}' has no non-null values.",
                "Drop this column or verify the data source.",
            ))
            continue  # skip further checks -- no data to inspect

        # Constant column
        if p["is_constant"]:
            findings.append(_finding(
                "LOW", col, "Constant column",
                f"'{col}' contains only one distinct value across all rows.",
                "This column carries no discriminating information; consider dropping it.",
            ))

        # Missing values
        if p["n_missing"] > 0:
            pct = p["missing_pct"]
            if pct >= 50:
                severity = "HIGH"
            elif pct >= 20:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            findings.append(_finding(
                severity, col, "Missing values",
                f"'{col}' has {p['n_missing']:,} missing values ({pct:.1f}%).",
                "Choose an imputation strategy or drop rows in the Cleaning tab.",
            ))

        # Numeric strings
        if p["is_numeric_string"]:
            findings.append(_finding(
                "MEDIUM", col, "Numeric values stored as text",
                f"'{col}' is stored as {p['dtype']} but most non-null values parse as numbers.",
                "Use 'Fix types' in the Cleaning tab to convert to numeric.",
            ))

        # Date strings
        if p["is_date_string"]:
            findings.append(_finding(
                "LOW", col, "Date-like values stored as text",
                f"'{col}' is stored as {p['dtype']} but values appear to be dates.",
                "Parse this column as datetime to enable time-series analysis.",
            ))

        # High cardinality (text columns with almost all unique values).
        # Uses _is_text_dtype to cover object, string, and the pandas 3.x
        # native "str" dtype without hard-coding an exhaustive list.
        if (
            _is_text_dtype(str(p["dtype"]))
            and not p["is_numeric_string"]
            and not p["is_date_string"]
            and n_rows > 10
            and p["n_unique"] >= 0.9 * (n_rows - p["n_missing"])
            and p["n_unique"] > 10
        ):
            findings.append(_finding(
                "INFO", col, "High cardinality text column",
                f"'{col}' has {p['n_unique']:,} unique values "
                f"({p['n_unique'] / max(n_rows - p['n_missing'], 1):.0%} of non-null rows).",
                "This may be a free-text or ID column. Aggregation may not be meaningful.",
            ))

        # Zero-variance numeric (std = 0, not already caught as constant)
        if (
            p["std"] is not None
            and p["std"] == 0.0
            and not p["is_constant"]
        ):
            findings.append(_finding(
                "LOW", col, "Zero-variance numeric column",
                f"'{col}' has std = 0; all non-null values are identical.",
                "This column contributes no variance. Consider dropping it.",
            ))

    return _sorted_findings(findings)


def _sorted_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(
        findings,
        key=lambda f: (_SEVERITY_ORDER.get(f["severity"], 99), f["column"]),
    )
