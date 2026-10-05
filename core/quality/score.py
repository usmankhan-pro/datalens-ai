"""Quality scoring utilities for DataLens AI."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from core.profiling.profile import profile_dataframe
from core.quality.issues import detect_issues


def _grade_for_score(score: float) -> str:
    """Map a quality score to a grade band."""
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 60:
        return "Fair"
    if score >= 40:
        return "Poor"
    return "Critical"


def _safe_score(raw: float) -> float:
    return float(max(0.0, min(100.0, raw)))


def analyze_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute the overall quality score for a DataFrame and return the metric tree."""
    if df is None or df.empty:
        return {
            "overall_score": 100.0,
            "grade": "Excellent",
            "dimensions": {},
            "issues": [],
            "summary": {"total_issues": 0, "critical_issues": 0, "warning_issues": 0},
        }

    profile = profile_dataframe(df)
    issues = detect_issues(df, profile)

    total_cells = int(df.size)
    missing_cells = int(df.isna().sum().sum())
    completeness = 100 * (1 - (missing_cells / total_cells)) if total_cells else 100.0

    duplicate_rows = int(df.duplicated().sum())
    uniqueness = 100 * (1 - (duplicate_rows / len(df))) if len(df) else 100.0
    if any(issue["type"] == "duplicate_ids" for issue in issues):
        uniqueness = max(0.0, uniqueness - 10)

    invalid_values = sum(issue["affected_rows"] for issue in issues if issue["type"] in {"negative_values", "inconsistent_format"})
    checked_values = max(1, int(df.notna().sum().sum()))
    validity = 100 * (1 - (invalid_values / checked_values))

    consistency_penalty = 0
    for issue in issues:
        if issue["type"] == "mixed_types":
            consistency_penalty += 5
        elif issue["type"] == "inconsistent_format":
            consistency_penalty += 3
        elif issue["type"] == "constant_column":
            consistency_penalty += 2
    consistency = max(0.0, 100 - min(30, consistency_penalty))

    outlier_share = 0.0
    for issue in issues:
        if issue["type"] == "outliers":
            outlier_share = max(outlier_share, issue["affected_pct"] / 100)
    accuracy_indicator = 100 - min(40, outlier_share * 100)

    overall_score = (
        0.30 * completeness
        + 0.15 * uniqueness
        + 0.25 * validity
        + 0.20 * consistency
        + 0.10 * accuracy_indicator
    )
    overall_score = _safe_score(overall_score)
    grade = _grade_for_score(overall_score)

    dimensions = {
        "Completeness": {
            "score": round(completeness, 2),
            "formula": "100 * (1 - missing_cells / total_cells)",
            "inputs": {"missing_cells": missing_cells, "total_cells": total_cells},
            "explanation": "Measures how much of the dataset is populated rather than blank.",
        },
        "Uniqueness": {
            "score": round(uniqueness, 2),
            "formula": "100 * (1 - duplicate_rows / total_rows)",
            "inputs": {"duplicate_rows": duplicate_rows, "total_rows": len(df)},
            "explanation": "Rewards datasets with fewer repeated records and penalizes ID duplication.",
        },
        "Validity": {
            "score": round(validity, 2),
            "formula": "100 * (1 - invalid_values / checked_values)",
            "inputs": {"invalid_values": invalid_values, "checked_values": checked_values},
            "explanation": "Checks whether values are parseable and fit expected business constraints.",
        },
        "Consistency": {
            "score": round(consistency, 2),
            "formula": "100 - penalties for mixed types, inconsistent formatting, and constant columns",
            "inputs": {"penalty_total": consistency_penalty},
            "explanation": "Measures whether columns follow a coherent structure and naming convention.",
        },
        "Accuracy / Validity Indicator": {
            "score": round(accuracy_indicator, 2),
            "formula": "100 - extreme_outlier_penalty",
            "inputs": {"outlier_share_pct": round(outlier_share * 100, 2)},
            "explanation": "This is an indicator, not proof of real-world accuracy; it highlights extreme outliers.",
        },
    }

    result = {
        "overall_score": round(overall_score, 2),
        "grade": grade,
        "dimensions": dimensions,
        "issues": issues,
        "summary": {
            "total_issues": len(issues),
            "critical_issues": sum(1 for issue in issues if issue["severity"] == "CRITICAL"),
            "warning_issues": sum(1 for issue in issues if issue["severity"] in {"MEDIUM", "HIGH"}),
        },
    }
    return result


__all__ = ["analyze_quality"]
