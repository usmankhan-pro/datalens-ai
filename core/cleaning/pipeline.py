"""Cleaning pipeline for DataLens AI.

Supports preview/apply semantics for a small set of cleaning operations used in
Phase 3. The original dataset is never mutated; operations act on a working copy
and return metadata for preview and audit logs.
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd


def _rows_affected(before: pd.DataFrame, after: pd.DataFrame) -> int:
    """Return the number of rows changed between before and after frames."""
    if before.shape != after.shape:
        return int(abs(len(before) - len(after)))
    return int((before != after).any(axis=1).sum())


def preview_operation(df: pd.DataFrame, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Return a preview of the cleaning operation without mutating the dataframe."""
    preview_df = df.copy()
    rows_affected = 0

    if operation == "remove_duplicates":
        before_rows = len(preview_df)
        preview_df = preview_df.drop_duplicates().copy()
        rows_affected = before_rows - len(preview_df)
    elif operation == "fill_missing_numeric":
        method = params.get("method", "mean")
        original_missing = df.select_dtypes(include=['number']).isna().sum().sum()
        for col in preview_df.select_dtypes(include=['number']).columns:
            series = preview_df[col]
            if method == "mean":
                fill_value = series.mean()
            elif method == "median":
                fill_value = series.median()
            else:
                fill_value = series.mode().iloc[0] if not series.mode().empty else 0
            preview_df[col] = series.fillna(fill_value)
        rows_affected = int(original_missing)
    elif operation == "standardize_text":
        case = params.get("case", "upper")
        strip = params.get("strip", True)
        for col in preview_df.columns:
            if not (pd.api.types.is_object_dtype(preview_df[col]) or pd.api.types.is_string_dtype(preview_df[col])):
                continue
            series = preview_df[col].astype(str)
            if strip:
                series = series.str.strip()
            if case == "upper":
                series = series.str.upper()
            elif case == "lower":
                series = series.str.lower()
            elif case == "title":
                series = series.str.title()
            preview_df[col] = series
        rows_affected = int((preview_df.astype(str) != df.astype(str)).any(axis=1).sum())
    else:
        raise ValueError(f"Unsupported operation: {operation}")

    return {
        "operation": operation,
        "rows_affected": int(rows_affected),
        "before": df.copy(),
        "after": preview_df,
        "preview": preview_df.head(),
    }


def apply_operation(df: pd.DataFrame, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Apply a cleaning operation to a working dataframe and return the result."""
    preview = preview_operation(df, operation, params)
    updated_df = preview["after"].copy()
    return {
        "df": updated_df,
        "rows_affected": int(preview["rows_affected"]),
        "operation": operation,
        "params": params,
    }


def export_history_script(history: List[Any]) -> str:
    """Convert an audit log into a reproducible pandas script."""
    lines = ["import pandas as pd", "", "df = pd.DataFrame()"]
    for item in history:
        lines.append(f"# {item.operation} | rows_affected={item.rows_affected}")
        if item.operation == "fill_missing_numeric":
            lines.append("df[col] = df[col].fillna(df[col].mean())")
        elif item.operation == "standardize_text":
            lines.append("df[col] = df[col].astype(str).str.strip().str.upper()")
    return "\n".join(lines)


__all__ = ["preview_operation", "apply_operation", "export_history_script"]
