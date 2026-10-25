"""Report generation: assembles quality, cleaning, and EDA results into exportable structures."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.analysis.descriptive import dataset_overview, all_column_profiles
from src.analysis.recommendations import generate_insights, recommendations_for_cleaning
from src.quality.quality_score import compute_quality_score, format_quality_report
from src.quality.issue_detection import detect_issues, rank_by_importance


def build_quality_report(
    data: pd.DataFrame,
    quality_result=None,
) -> dict[str, Any]:
    """Build a complete quality-assessment report dict."""
    if quality_result is None:
        quality_result = compute_quality_score(data)

    findings = detect_issues(data)
    ranked_findings = rank_by_importance(findings)

    return {
        "generated_at": datetime.now().isoformat(),
        "dataset": {
            "n_rows": int(quality_result.n_rows),
            "n_cols": int(quality_result.n_cols),
        },
        "overall_score": quality_result.overall_score,
        "overall_label": quality_result.overall_label,
        "interpretation": quality_result.overall_interpretation,
        "recommendation": quality_result.overall_recommendation,
        "dimensions": format_quality_report(quality_result),
        "excluded_dimensions": quality_result.excluded_dimensions,
        "findings": ranked_findings,
        "n_findings": len(ranked_findings),
    }


def build_cleaning_report(
    original_data: pd.DataFrame,
    cleaned_data: pd.DataFrame,
    cleaning_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a cleaning audit report comparing before/after."""
    from src.quality.quality_score import compute_quality_score as _score

    before_score = _score(original_data)
    after_score = _score(cleaned_data)

    return {
        "generated_at": datetime.now().isoformat(),
        "original": {
            "n_rows": len(original_data),
            "n_cols": len(original_data.columns),
            "quality_score": before_score.overall_score,
            "quality_label": before_score.overall_label,
        },
        "cleaned": {
            "n_rows": len(cleaned_data),
            "n_cols": len(cleaned_data.columns),
            "quality_score": after_score.overall_score,
            "quality_label": after_score.overall_label,
        },
        "changes": {
            "rows_removed": len(original_data) - len(cleaned_data),
            "rows_added": len(cleaned_data) - len(original_data),
            "columns_added": len(cleaned_data.columns) - len(original_data.columns),
            "columns_removed": len(original_data.columns) - len(cleaned_data.columns),
        },
        "score_change": round(after_score.overall_score - before_score.overall_score, 2),
        "operations": cleaning_records,
        "n_operations": len(cleaning_records),
    }


def build_eda_report(
    data: pd.DataFrame,
    selected_columns: list[str] | None = None,
) -> dict[str, Any]:
    """Build an EDA report with overviews, profiles, and insights."""
    overview = dataset_overview(data)
    profiles = all_column_profiles(data)
    insights = generate_insights(data)

    if selected_columns is None:
        selected_columns = list(data.columns)
    selected_profiles = {c: profiles.get(c, {}) for c in selected_columns if c in profiles}

    return {
        "generated_at": datetime.now().isoformat(),
        "overview": overview,
        "column_profiles": selected_profiles,
        "insights": insights,
        "n_insights": len(insights),
    }


def build_full_report(
    original_data: pd.DataFrame,
    cleaned_data: pd.DataFrame,
    cleaning_records: list[dict[str, Any]],
    quality_result=None,
) -> dict[str, Any]:
    """Build a comprehensive report covering quality, cleaning, and EDA."""
    quality_report = build_quality_report(cleaned_data, quality_result)
    cleaning_report = build_cleaning_report(original_data, cleaned_data, cleaning_records)
    eda_report = build_eda_report(cleaned_data)

    return {
        "generated_at": datetime.now().isoformat(),
        "quality": quality_report,
        "cleaning": cleaning_report,
        "eda": eda_report,
        "summary": {
            "original_quality_score": cleaning_report["original"]["quality_score"],
            "cleaned_quality_score": cleaning_report["cleaned"]["quality_score"],
            "score_change": cleaning_report["score_change"],
            "n_operations": cleaning_report["n_operations"],
            "n_rows_before": cleaning_report["original"]["n_rows"],
            "n_rows_after": cleaning_report["cleaned"]["n_rows"],
        },
    }
