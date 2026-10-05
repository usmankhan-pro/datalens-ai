"""Issue detection helpers for DataLens AI quality scoring."""

from __future__ import annotations

import re
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from core.profiling.profile import profile_dataframe


SEVERITY_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _severity_for_pct(metric: str, pct: float) -> str:
    """Map a percentage to a severity label following the project thresholds."""
    if metric == "missing":
        if pct < 5:
            return "LOW"
        if pct < 15:
            return "MEDIUM"
        if pct < 40:
            return "HIGH"
        return "CRITICAL"
    if metric == "duplicate_rows":
        if pct < 1:
            return "LOW"
        if pct < 5:
            return "MEDIUM"
        if pct < 15:
            return "HIGH"
        return "CRITICAL"
    if metric == "invalid":
        if pct < 1:
            return "LOW"
        if pct < 5:
            return "MEDIUM"
        if pct < 15:
            return "HIGH"
        return "CRITICAL"
    if metric == "outlier":
        if pct < 1:
            return "LOW"
        if pct < 3:
            return "MEDIUM"
        if pct < 7:
            return "HIGH"
        return "CRITICAL"
    if metric in {"mixed_types", "inconsistent_format", "constant_column"}:
        return "MEDIUM" if pct > 0 else "LOW"
    return "LOW"


def _issue(type_name: str, column: str, affected_rows: int, total_rows: int, severity: str, explanation: str, suggested_action: str) -> Dict[str, Any]:
    affected_pct = (affected_rows / total_rows * 100) if total_rows else 0.0
    return {
        "type": type_name,
        "column": column,
        "affected_rows": int(affected_rows),
        "affected_pct": float(round(affected_pct, 2)),
        "severity": severity,
        "explanation": explanation,
        "suggested_action": suggested_action,
    }


def detect_issues(df: pd.DataFrame, profile: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """Return a list of issue objects for the dataset."""
    if df is None or df.empty:
        return []

    profile = profile or profile_dataframe(df)
    issues: List[Dict[str, Any]] = []
    total_rows = len(df)

    for column_name in df.columns:
        series = df[column_name]
        missing_count = int(series.isna().sum())
        if missing_count:
            pct = (missing_count / total_rows * 100) if total_rows else 0.0
            severity = _severity_for_pct("missing", pct)
            issues.append(
                _issue(
                    "missing_values",
                    column_name,
                    missing_count,
                    total_rows,
                    severity,
                    f"{missing_count} missing values were found in '{column_name}'.",
                    f"Review '{column_name}' and fill or remove incomplete records.",
                )
            )

        if series.dtype.kind in "O":
            string_values = series.dropna().astype(str)
            stripped = string_values.str.strip()
            lowered = stripped.str.lower()
            if not stripped.empty and lowered.nunique() > 1:
                variant_count = int((lowered != stripped).sum() + (stripped != lowered).sum())
                if variant_count:
                    issues.append(
                        _issue(
                            "inconsistent_format",
                            column_name,
                            int(variant_count),
                            total_rows,
                            _severity_for_pct("inconsistent_format", variant_count / total_rows * 100),
                            f"Text casing and whitespace vary in '{column_name}'.",
                            f"Standardize the text values in '{column_name}' to a single casing and trimming style.",
                        )
                    )

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        for column_name in numeric_cols:
            series = df[column_name]
            negative_mask = series < 0
            if negative_mask.any():
                neg_count = int(negative_mask.sum())
                issues.append(
                    _issue(
                        "negative_values",
                        column_name,
                        neg_count,
                        total_rows,
                        _severity_for_pct("invalid", (neg_count / total_rows) * 100),
                        f"Negative values were found in '{column_name}'.",
                        f"Check whether negative values in '{column_name}' are valid or should be treated as missing/invalid.",
                    )
                )

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            if pd.notna(q1) and pd.notna(q3):
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                outlier_count = int(((series < lower) | (series > upper)).sum())
                if outlier_count:
                    pct = (outlier_count / total_rows) * 100 if total_rows else 0
                    issues.append(
                        _issue(
                            "outliers",
                            column_name,
                            outlier_count,
                            total_rows,
                            _severity_for_pct("outlier", pct),
                            f"Potential outliers were detected in '{column_name}'.",
                            f"Inspect or cap extreme values in '{column_name}' before key calculations.",
                        )
                    )

    if total_rows and df.duplicated().any():
        dup_rows = int(df.duplicated().sum())
        issues.append(
            _issue(
                "duplicate_rows",
                "dataset",
                dup_rows,
                total_rows,
                _severity_for_pct("duplicate_rows", (dup_rows / total_rows) * 100),
                f"{dup_rows} duplicate rows were found in the dataset.",
                "Remove duplicate rows or review whether they represent repeated transactions.",
            )
        )

    for column_name in df.columns:
        series = df[column_name]
        if series.nunique(dropna=True) <= 1:
            issues.append(
                _issue(
                    "constant_column",
                    column_name,
                    int(series.isna().sum() + 1),
                    total_rows,
                    _severity_for_pct("constant_column", 0),
                    f"'{column_name}' contains a constant value across the dataset.",
                    f"Review whether '{column_name}' adds value or can be dropped from analysis.",
                )
            )

    for column_name in df.columns:
        series = df[column_name]
        if any(token in str(column_name).lower() for token in ["id", "customer", "client", "user", "code"]):
            value_counts = series.dropna().value_counts()
            dup_ids = int((value_counts > 1).sum())
            if dup_ids:
                issues.append(
                    _issue(
                        "duplicate_ids",
                        column_name,
                        dup_ids,
                        total_rows,
                        "HIGH",
                        f"Duplicate identifiers were found in '{column_name}'.",
                        "Review the identifier column for duplicate records or merge issues.",
                    )
                )

    for column_name in df.columns:
        series = df[column_name]
        if series.dtype == object:
            mixed = False
            for value in series.dropna().astype(str):
                has_digit = bool(re.search(r"\d", value))
                has_letter = bool(re.search(r"[A-Za-z]", value))
                if has_digit and has_letter:
                    mixed = True
                    break
            if mixed:
                issues.append(
                    _issue(
                        "mixed_types",
                        column_name,
                        int(series.dropna().shape[0]),
                        total_rows,
                        "MEDIUM",
                        f"'{column_name}' appears to contain mixed text and numeric values.",
                        f"Normalize '{column_name}' to a single consistent value type before analysis.",
                    )
                )

    return issues


__all__ = ["detect_issues"]
