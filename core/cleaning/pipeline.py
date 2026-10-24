"""End-to-end cleaning pipeline for DataLens AI.

Implements an 8-stage ordered cleaning architecture:
1. Structure (headers, empty rows/cols, snake_case names)
2. Types (numeric text, dates, booleans)
3. Text (trim, case, variants)
4. Invalid values and placeholders (N/A, -, 999)
5. Duplicates
6. Missing values (per-column strategy)
7. Outliers (flag by default; cap/remove only on approval)
8. Final validation

Rules:
- The original DataFrame is NEVER modified. All operations return a working copy.
- Risky operations always require approval.
- "Auto-clean (safe steps only)" runs all safe non-destructive operations automatically.
- Every operation records exact metadata: step, column, rows affected, params, timestamp.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from core.utils.state import TransformRecord

# Ordered list of pipeline stages
CLEANING_STAGES = [
    "structure",
    "types",
    "text",
    "invalid_values",
    "duplicates",
    "missing_values",
    "outliers",
    "validation",
]

DEFAULT_PLACEHOLDERS = [
    "N/A", "n/a", "NA", "na", "-", "--", "---",
    "none", "None", "NONE", "null", "Null", "NULL",
    "999", "-999", "9999", "?", "???", "",
]

BOOL_MAPPINGS = {
    "true": True, "1": True, "yes": True, "y": True, "t": True,
    "false": False, "0": False, "no": False, "n": False, "f": False,
}


def _rows_changed(before: pd.DataFrame, after: pd.DataFrame) -> int:
    """Compute number of rows altered or dropped."""
    if len(before) != len(after):
        return int(abs(len(before) - len(after)))
    if set(before.columns) != set(after.columns):
        return int(len(before))
    try:
        # Align column names for comparison
        common_cols = [c for c in before.columns if c in after.columns]
        diff = (before[common_cols].astype(str) != after[common_cols].astype(str)).any(axis=1)
        return int(diff.sum())
    except Exception:
        return 0


def to_snake_case(name: str) -> str:
    """Normalize a string column name to snake_case."""
    s = re.sub(r"[\s\-\.]+", "_", str(name).strip())
    s = re.sub(r"[^\w]", "", s)
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)
    s = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_").lower() or "unnamed_column"


# ---------------------------------------------------------
# Stage 1: Structure
# ---------------------------------------------------------

def clean_structure_drop_empty_rows(df: pd.DataFrame, how: str = "all") -> Tuple[pd.DataFrame, int]:
    """Drop rows where all (or any) cells are NaN."""
    before_rows = len(df)
    res = df.dropna(how=how).copy()
    return res, before_rows - len(res)


def clean_structure_drop_empty_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Drop columns that contain 100% NaN values."""
    before_cols = len(df.columns)
    res = df.dropna(axis=1, how="all").copy()
    return res, before_cols - len(res.columns)


def clean_structure_snake_case_names(df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
    """Rename all column headers to consistent snake_case."""
    res = df.copy()
    new_names = [to_snake_case(c) for c in res.columns]
    # Ensure unique column names if duplicates arise
    seen: Dict[str, int] = {}
    unique_names: List[str] = []
    for name in new_names:
        if name in seen:
            seen[name] += 1
            unique_names.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            unique_names.append(name)
    changed = sum(1 for old, new in zip(res.columns, unique_names) if str(old) != new)
    res.columns = unique_names
    return res, changed


# ---------------------------------------------------------
# Stage 2: Types
# ---------------------------------------------------------

def clean_types_numeric_text(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Tuple[pd.DataFrame, int]:
    """Convert currency, percentage, and formatted number strings into numeric floats."""
    res = df.copy()
    target_cols = columns or [c for c in res.columns if res[c].dtype == "object" or pd.api.types.is_string_dtype(res[c])]
    rows_affected = 0

    for col in target_cols:
        if col not in res.columns:
            continue
        series = res[col]
        # Quick heuristic: contains $, %, commas, parentheses
        sample = series.dropna().astype(str).head(50)
        has_num_char = sample.str.contains(r"[\$,%]|^\s*\([0-9\.]+\)\s*$", regex=True).any()
        if not has_num_char and columns is None:
            continue

        cleaned = (
            series.astype(str)
            .str.replace(r"[\$,%]", "", regex=True)
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
            .str.strip()
        )
        # Attempt conversion
        converted = pd.to_numeric(cleaned, errors="coerce")
        # If conversion is mostly successful on non-null values
        valid_ratio = converted.notna().sum() / max(1, series.notna().sum())
        if valid_ratio >= 0.7 or (columns and col in columns):
            chg = int((converted.notna() & (converted != series)).sum())
            res[col] = converted
            rows_affected += chg

    return res, rows_affected


def clean_types_dates(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Tuple[pd.DataFrame, int]:
    """Parse date-like string columns into datetime objects."""
    res = df.copy()
    target_cols = columns or [c for c in res.columns if res[c].dtype == "object" or pd.api.types.is_string_dtype(res[c])]
    rows_affected = 0

    for col in target_cols:
        if col not in res.columns:
            continue
        series = res[col].dropna()
        if series.empty:
            continue

        # Check date hints in column name or content
        is_date_col = any(h in col.lower() for h in ["date", "time", "day", "created", "updated"]) or (columns and col in columns)
        if not is_date_col:
            continue

        try:
            converted = pd.to_datetime(res[col], errors="coerce")
            if converted.notna().mean() >= 0.6 or (columns and col in columns):
                chg = int(converted.notna().sum())
                res[col] = converted
                rows_affected += chg
        except Exception:
            continue

    return res, rows_affected


def clean_types_booleans(df: pd.DataFrame, columns: Optional[List[str]] = None) -> Tuple[pd.DataFrame, int]:
    """Convert boolean-like text (yes/no, true/false, 1/0) into boolean columns."""
    res = df.copy()
    target_cols = columns or [c for c in res.columns if res[c].dtype == "object" or pd.api.types.is_string_dtype(res[c])]
    rows_affected = 0

    for col in target_cols:
        if col not in res.columns:
            continue
        series = res[col].dropna().astype(str).str.strip().str.lower()
        if series.empty:
            continue
        unique = set(series.unique())
        if unique.issubset(set(BOOL_MAPPINGS.keys())):
            mapped = res[col].astype(str).str.strip().str.lower().map(BOOL_MAPPINGS)
            chg = int(mapped.notna().sum())
            res[col] = mapped
            rows_affected += chg

    return res, rows_affected


# ---------------------------------------------------------
# Stage 3: Text
# ---------------------------------------------------------

def clean_text_standardize(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    case: str = "preserve",
    strip: bool = True,
    collapse_spaces: bool = True,
) -> Tuple[pd.DataFrame, int]:
    """Trim whitespace, collapse internal spaces, and standardize text casing."""
    res = df.copy()
    target_cols = columns or [c for c in res.columns if res[c].dtype == "object" or pd.api.types.is_string_dtype(res[c])]
    rows_affected = 0

    for col in target_cols:
        if col not in res.columns:
            continue
        original = res[col].copy()
        series = res[col].astype(str)

        if strip:
            series = series.str.strip()
        if collapse_spaces:
            series = series.str.replace(r"\s+", " ", regex=True)
        if case == "lower":
            series = series.str.lower()
        elif case == "upper":
            series = series.str.upper()
        elif case == "title":
            series = series.str.title()

        # Restore original NaNs
        series[original.isna()] = np.nan
        chg = int(((series != original) & original.notna()).sum())
        res[col] = series
        rows_affected += chg

    return res, rows_affected


def clean_text_harmonize_variants(
    df: pd.DataFrame,
    column: str,
    mapping: Dict[str, str],
) -> Tuple[pd.DataFrame, int]:
    """Replace specific string variants using a mapping dictionary."""
    res = df.copy()
    if column not in res.columns or not mapping:
        return res, 0

    original = res[column].copy()
    res[column] = res[column].replace(mapping)
    chg = int((res[column] != original).sum())
    return res, chg


# ---------------------------------------------------------
# Stage 4: Invalid Values and Placeholders
# ---------------------------------------------------------

def clean_invalid_placeholders(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    placeholders: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, int]:
    """Replace common sentinel values ('N/A', '-', '999', '?') with actual NaNs."""
    res = df.copy()
    targets = placeholders or DEFAULT_PLACEHOLDERS
    cols = columns or list(res.columns)
    rows_affected = 0

    for col in cols:
        if col not in res.columns:
            continue
        original_missing = int(res[col].isna().sum())
        # Check both direct match and stripped string match
        series_str = res[col].astype(str).str.strip()
        mask = res[col].isin(targets) | series_str.isin(targets)
        # Avoid treating valid small numbers as 999
        if pd.api.types.is_numeric_dtype(res[col]):
            mask = res[col].isin([999, -999, 9999, -9999])

        if mask.any():
            res.loc[mask, col] = np.nan
            new_missing = int(res[col].isna().sum())
            rows_affected += (new_missing - original_missing)

    return res, rows_affected


# ---------------------------------------------------------
# Stage 5: Duplicates
# ---------------------------------------------------------

def clean_duplicates_remove(
    df: pd.DataFrame,
    subset: Optional[List[str]] = None,
    keep: str = "first",
) -> Tuple[pd.DataFrame, int]:
    """Remove exact or subset duplicate rows."""
    before_rows = len(df)
    res = df.drop_duplicates(subset=subset, keep=keep).copy()
    return res, before_rows - len(res)


# ---------------------------------------------------------
# Stage 6: Missing Values
# ---------------------------------------------------------

def clean_missing_impute(
    df: pd.DataFrame,
    column: str,
    strategy: str = "median",
    constant_value: Any = None,
) -> Tuple[pd.DataFrame, int]:
    """Impute missing values in a column using mean, median, mode, constant, or forward-fill."""
    res = df.copy()
    if column not in res.columns:
        return res, 0

    series = res[column]
    missing_count = int(series.isna().sum())
    if missing_count == 0:
        return res, 0

    if strategy == "mean" and pd.api.types.is_numeric_dtype(series):
        val = series.mean()
        res[column] = series.fillna(val)
    elif strategy == "median" and pd.api.types.is_numeric_dtype(series):
        val = series.median()
        res[column] = series.fillna(val)
    elif strategy == "mode":
        val = series.mode().iloc[0] if not series.mode().empty else ("Unknown" if series.dtype == "object" else 0)
        res[column] = series.fillna(val)
    elif strategy == "constant":
        val = constant_value if constant_value is not None else ("Unknown" if series.dtype == "object" else 0)
        res[column] = series.fillna(val)
    elif strategy == "ffill":
        res[column] = series.ffill().bfill()
    elif strategy == "drop_rows":
        res = res.dropna(subset=[column]).copy()
        return res, missing_count
    else:
        # Fallback to median for numeric, mode for categorical
        if pd.api.types.is_numeric_dtype(series):
            res[column] = series.fillna(series.median())
        else:
            mode_val = series.mode().iloc[0] if not series.mode().empty else "Unknown"
            res[column] = series.fillna(mode_val)

    return res, missing_count


def clean_missing_drop_columns(df: pd.DataFrame, threshold_pct: float = 50.0) -> Tuple[pd.DataFrame, int]:
    """Drop columns where missing value percentage exceeds threshold."""
    before_cols = len(df.columns)
    cutoff = threshold_pct / 100.0
    keep_cols = [c for c in df.columns if df[c].isna().mean() <= cutoff]
    res = df[keep_cols].copy()
    return res, before_cols - len(keep_cols)


# ---------------------------------------------------------
# Stage 7: Outliers
# ---------------------------------------------------------

def detect_outliers_iqr(series: pd.Series, factor: float = 1.5) -> pd.Series:
    """Return boolean mask of outliers based on IQR fences."""
    if not pd.api.types.is_numeric_dtype(series):
        return pd.Series(False, index=series.index)
    valid = series.dropna()
    if len(valid) < 4:
        return pd.Series(False, index=series.index)
    q25 = valid.quantile(0.25)
    q75 = valid.quantile(0.75)
    iqr = q75 - q25
    if iqr == 0:
        return pd.Series(False, index=series.index)
    lower = q25 - factor * iqr
    upper = q75 + factor * iqr
    return (series < lower) | (series > upper)


def clean_outliers_cap(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    factor: float = 1.5,
) -> Tuple[pd.DataFrame, int]:
    """Winsorize / cap values to IQR boundaries (requires approval - risky)."""
    res = df.copy()
    num_cols = columns or [c for c in res.columns if pd.api.types.is_numeric_dtype(res[c])]
    total_capped = 0

    for col in num_cols:
        if col not in res.columns or not pd.api.types.is_numeric_dtype(res[col]):
            continue
        valid = res[col].dropna()
        if len(valid) < 4:
            continue
        q25 = valid.quantile(0.25)
        q75 = valid.quantile(0.75)
        iqr = q75 - q25
        if iqr == 0:
            continue
        lower = q25 - factor * iqr
        upper = q75 + factor * iqr

        outlier_mask = (res[col] < lower) | (res[col] > upper)
        cnt = int(outlier_mask.sum())
        if cnt > 0:
            res[col] = res[col].clip(lower=lower, upper=upper)
            total_capped += cnt

    return res, total_capped


def clean_outliers_remove(
    df: pd.DataFrame,
    columns: Optional[List[str]] = None,
    factor: float = 1.5,
) -> Tuple[pd.DataFrame, int]:
    """Remove rows containing outlier values (requires approval - risky)."""
    res = df.copy()
    num_cols = columns or [c for c in res.columns if pd.api.types.is_numeric_dtype(res[c])]
    before_rows = len(res)

    for col in num_cols:
        if col not in res.columns or not pd.api.types.is_numeric_dtype(res[col]):
            continue
        outlier_mask = detect_outliers_iqr(res[col], factor=factor)
        res = res[~outlier_mask].copy()

    return res, before_rows - len(res)


# ---------------------------------------------------------
# Stage 8: Final Validation
# ---------------------------------------------------------

def clean_validate_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """Run integrity validation on the cleaned dataset."""
    total_cells = int(df.size)
    missing_cells = int(df.isna().sum().sum())
    missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
    duplicates = int(df.duplicated().sum())

    dtypes_summary = {str(k): int(v) for k, v in df.dtypes.value_counts().items()}

    return {
        "rows": len(df),
        "cols": len(df.columns),
        "missing_cells": missing_cells,
        "missing_pct": round(missing_pct, 2),
        "duplicate_rows": duplicates,
        "dtypes": dtypes_summary,
        "is_empty": df.empty,
        "valid": not df.empty and missing_pct < 100.0,
    }


# ---------------------------------------------------------
# Unified Operation Dispatcher & Auto-Clean
# ---------------------------------------------------------

OPERATION_SPECS = {
    "drop_empty_rows": {
        "stage": "structure",
        "risk": "safe",
        "label": "Drop Empty Rows",
        "desc": "Removes rows where all cells are blank/NaN.",
    },
    "drop_empty_columns": {
        "stage": "structure",
        "risk": "safe",
        "label": "Drop Empty Columns",
        "desc": "Removes columns containing 100% missing values.",
    },
    "snake_case_columns": {
        "stage": "structure",
        "risk": "safe",
        "label": "Standardize Column Names",
        "desc": "Converts headers to clean lowercase snake_case.",
    },
    "convert_numeric_text": {
        "stage": "types",
        "risk": "safe",
        "label": "Convert Numeric Strings",
        "desc": "Strips currency symbols, commas, percentages, and casts to float.",
    },
    "parse_dates": {
        "stage": "types",
        "risk": "safe",
        "label": "Parse Dates",
        "desc": "Standardizes date/time strings into ISO datetime format.",
    },
    "convert_booleans": {
        "stage": "types",
        "risk": "safe",
        "label": "Convert Booleans",
        "desc": "Converts yes/no, true/false, 1/0 text into boolean dtypes.",
    },
    "standardize_text": {
        "stage": "text",
        "risk": "safe",
        "label": "Standardize Text",
        "desc": "Trims leading/trailing whitespace and normalizes casing.",
    },
    "harmonize_variants": {
        "stage": "text",
        "risk": "review",
        "label": "Harmonize String Variants",
        "desc": "Replaces near-duplicate categorical labels using mapping.",
    },
    "replace_placeholders": {
        "stage": "invalid_values",
        "risk": "safe",
        "label": "Clean Sentinel Placeholders",
        "desc": "Converts sentinel values ('N/A', '-', '999', '?') to actual NaNs.",
    },
    "remove_duplicates": {
        "stage": "duplicates",
        "risk": "safe",
        "label": "Remove Exact Duplicates",
        "desc": "Drops fully identical rows keeping the first occurrence.",
    },
    "fill_missing_numeric": {
        "stage": "missing_values",
        "risk": "review",
        "label": "Impute Missing Numeric",
        "desc": "Fills missing numbers using median, mean, mode, or constant.",
    },
    "fill_missing_categorical": {
        "stage": "missing_values",
        "risk": "review",
        "label": "Impute Missing Categorical",
        "desc": "Fills missing categories using mode or 'Unknown'.",
    },
    "drop_missing_columns": {
        "stage": "missing_values",
        "risk": "risky",
        "label": "Drop Heavy-Missing Columns",
        "desc": "Removes columns with missingness exceeding threshold.",
    },
    "cap_outliers": {
        "stage": "outliers",
        "risk": "risky",
        "label": "Cap Outliers (Winsorize)",
        "desc": "Clips extreme values outside IQR fences to boundaries (requires approval).",
    },
    "remove_outliers": {
        "stage": "outliers",
        "risk": "risky",
        "label": "Remove Outlier Rows",
        "desc": "Drops rows with values outside IQR fences (requires approval).",
    },
}


def preview_operation(df: pd.DataFrame, operation: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generate a non-mutating preview of a cleaning step."""
    params = params or {}
    updated_df, rows_affected = _dispatch_operation(df.copy(), operation, params)
    spec = OPERATION_SPECS.get(operation, {"stage": "custom", "risk": "review"})

    return {
        "operation": operation,
        "stage": spec.get("stage", "cleaning"),
        "risk": spec.get("risk", "safe"),
        "rows_affected": int(rows_affected),
        "before": df.copy(),
        "after": updated_df,
        "preview": updated_df.head(10),
    }


def apply_operation(df: pd.DataFrame, operation: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Apply a cleaning operation to a working dataframe."""
    params = params or {}
    updated_df, rows_affected = _dispatch_operation(df.copy(), operation, params)
    spec = OPERATION_SPECS.get(operation, {"stage": "custom", "risk": "review"})

    return {
        "df": updated_df,
        "rows_affected": int(rows_affected),
        "operation": operation,
        "stage": spec.get("stage", "cleaning"),
        "risk": spec.get("risk", "safe"),
        "params": params,
    }


def _dispatch_operation(df: pd.DataFrame, operation: str, params: Dict[str, Any]) -> Tuple[pd.DataFrame, int]:
    """Dispatch an operation name with arguments to its concrete implementation."""
    if operation == "drop_empty_rows":
        return clean_structure_drop_empty_rows(df, how=params.get("how", "all"))
    elif operation == "drop_empty_columns":
        return clean_structure_drop_empty_columns(df)
    elif operation == "snake_case_columns":
        return clean_structure_snake_case_names(df)
    elif operation == "convert_numeric_text":
        return clean_types_numeric_text(df, columns=params.get("columns"))
    elif operation == "parse_dates":
        return clean_types_dates(df, columns=params.get("columns"))
    elif operation == "convert_booleans":
        return clean_types_booleans(df, columns=params.get("columns"))
    elif operation == "standardize_text":
        return clean_text_standardize(
            df,
            columns=params.get("columns"),
            case=params.get("case", "preserve"),
            strip=params.get("strip", True),
            collapse_spaces=params.get("collapse_spaces", True),
        )
    elif operation == "harmonize_variants":
        return clean_text_harmonize_variants(df, column=params.get("column", ""), mapping=params.get("mapping", {}))
    elif operation == "replace_placeholders" or operation == "clean_invalid_placeholders":
        return clean_invalid_placeholders(
            df,
            columns=params.get("columns"),
            placeholders=params.get("placeholders", DEFAULT_PLACEHOLDERS),
        )
    elif operation == "remove_duplicates" or operation == "drop_duplicates":
        return clean_duplicates_remove(df, subset=params.get("subset"), keep=params.get("keep", "first"))
    elif operation == "fill_missing_numeric":
        cols = params.get("columns") or [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        tot = 0
        res = df.copy()
        for c in cols:
            res, aff = clean_missing_impute(res, column=c, strategy=params.get("method", "median"))
            tot += aff
        return res, tot
    elif operation == "fill_missing_categorical":
        cols = params.get("columns") or [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
        tot = 0
        res = df.copy()
        for c in cols:
            res, aff = clean_missing_impute(res, column=c, strategy=params.get("method", "mode"))
            tot += aff
        return res, tot
    elif operation == "drop_missing_columns":
        return clean_missing_drop_columns(df, threshold_pct=params.get("threshold_pct", 50.0))
    elif operation == "cap_outliers":
        return clean_outliers_cap(df, columns=params.get("columns"), factor=params.get("factor", 1.5))
    elif operation == "remove_outliers":
        return clean_outliers_remove(df, columns=params.get("columns"), factor=params.get("factor", 1.5))
    else:
        raise ValueError(f"Unsupported cleaning operation: {operation}")


def auto_clean_safe_steps(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[TransformRecord]]:
    """
    Execute all non-destructive, safe cleaning steps in the mandated order:
    Structure -> Types -> Text -> Invalid Values -> Duplicates.

    Does NOT execute risky steps (missing value dropping, capping/removing outliers).
    """
    working = df.copy()
    records: List[TransformRecord] = []

    # Safe sequence in exact 8-stage order
    safe_steps = [
        ("drop_empty_rows", {}, "structure"),
        ("drop_empty_columns", {}, "structure"),
        ("snake_case_columns", {}, "structure"),
        ("convert_numeric_text", {}, "types"),
        ("parse_dates", {}, "types"),
        ("convert_booleans", {}, "types"),
        ("standardize_text", {"strip": True, "case": "preserve"}, "text"),
        ("replace_placeholders", {}, "invalid_values"),
        ("remove_duplicates", {}, "duplicates"),
    ]

    for op, params, stage in safe_steps:
        working, aff = _dispatch_operation(working, op, params)
        if aff > 0 or op in {"snake_case_columns"}:
            records.append(
                TransformRecord(
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    operation=op,
                    columns=list(working.columns),
                    params=params,
                    rows_affected=aff,
                    stage=stage,
                    risk="safe",
                )
            )

    return working, records


def export_history_script(history: List[Any]) -> str:
    """Backward-compatible helper redirecting to script_generator."""
    from core.export.script_generator import generate_cleaning_script
    return generate_cleaning_script(history)


__all__ = [
    "CLEANING_STAGES",
    "OPERATION_SPECS",
    "preview_operation",
    "apply_operation",
    "auto_clean_safe_steps",
    "export_history_script",
    "clean_structure_drop_empty_rows",
    "clean_structure_drop_empty_columns",
    "clean_structure_snake_case_names",
    "clean_types_numeric_text",
    "clean_types_dates",
    "clean_types_booleans",
    "clean_text_standardize",
    "clean_invalid_placeholders",
    "clean_duplicates_remove",
    "clean_missing_impute",
    "clean_missing_drop_columns",
    "clean_outliers_cap",
    "clean_outliers_remove",
    "clean_validate_dataset",
]
