"""Insight generation and recommendation utilities for DataLens AI."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

import numpy as np
import pandas as pd


SEVERITY_SCORE = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to a numeric series with NaN for invalid entries."""
    return pd.to_numeric(series, errors="coerce")


def _sort_issues_by_severity(issues: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return issues sorted from most urgent to least urgent."""
    return sorted(
        issues,
        key=lambda item: SEVERITY_SCORE.get(str(item.get("severity", "LOW")).upper(), 1),
        reverse=True,
    )


def _build_issue_summary(quality_result: Dict[str, Any] | None) -> List[Dict[str, Any]]:
    """Safely extract issue records from a quality-result payload."""
    if not isinstance(quality_result, dict):
        return []
    issues = quality_result.get("issues", [])
    if isinstance(issues, list):
        return list(issues)
    return []


def generate_insights(df: pd.DataFrame, quality_result: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    """Generate dataset insights that are traceable to real metrics and issue summaries."""
    if df is None or df.empty:
        return []

    if quality_result is None:
        try:
            from core.quality import analyze_quality  # local import to avoid circular dependency

            quality_result = analyze_quality(df)
        except Exception:
            quality_result = {"issues": []}

    issues = _build_issue_summary(quality_result)
    insights: List[Dict[str, Any]] = []

    numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]

    if "Revenue" in df.columns:
        revenue = _coerce_numeric(df["Revenue"]).dropna()
        if not revenue.empty:
            total_revenue = float(revenue.sum())
            insights.append(
                {
                    "source_metric": "Revenue",
                    "value": round(total_revenue, 2),
                    "unit": "currency",
                    "category": "financial_performance",
                    "text": f"Revenue totals {total_revenue:,.2f} across the current dataset.",
                    "evidence_ref": "Revenue",
                    "status": "positive" if total_revenue >= 0 else "warning",
                }
            )

    if "Profit" in df.columns:
        profit = _coerce_numeric(df["Profit"]).dropna()
        if not profit.empty:
            total_profit = float(profit.sum())
            insights.append(
                {
                    "source_metric": "Profit",
                    "value": round(total_profit, 2),
                    "unit": "currency",
                    "category": "financial_performance",
                    "text": f"Net profit is {total_profit:,.2f} after cost deductions.",
                    "evidence_ref": "Profit",
                    "status": "positive" if total_profit >= 0 else "warning",
                }
            )

    if "Date" in df.columns:
        date_values = pd.to_datetime(df["Date"], errors="coerce").dropna()
        if not date_values.empty:
            start_date = date_values.min().strftime("%Y-%m-%d")
            end_date = date_values.max().strftime("%Y-%m-%d")
            insights.append(
                {
                    "source_metric": "Date",
                    "value": f"{start_date} to {end_date}",
                    "unit": "date_range",
                    "category": "coverage",
                    "text": f"Observations span from {start_date} through {end_date}.",
                    "evidence_ref": "Date",
                    "status": "neutral",
                }
            )

    if issues:
        issue_count = len(issues)
        critical_count = sum(1 for issue in issues if str(issue.get("severity", "")).upper() in {"HIGH", "CRITICAL"})
        score = float(quality_result.get("overall_score", 100.0)) if isinstance(quality_result, dict) else 100.0
        insights.append(
            {
                "source_metric": "quality_score",
                "value": round(score, 1),
                "unit": "score",
                "category": "data_quality",
                "text": f"Quality score is {score:.1f}, with {critical_count} critical/high-priority issues flagged across {issue_count} issues.",
                "evidence_ref": "quality_result",
                "status": "warning" if critical_count else "positive",
            }
        )

    if not insights:
        if numeric_columns:
            first_numeric = numeric_columns[0]
            first_series = _coerce_numeric(df[first_numeric]).dropna()
            if not first_series.empty:
                insights.append(
                    {
                        "source_metric": first_numeric,
                        "value": float(first_series.mean()),
                        "unit": "average",
                        "category": "distribution",
                        "text": f"The average value in {first_numeric} is {first_series.mean():,.2f}.",
                        "evidence_ref": first_numeric,
                        "status": "neutral",
                    }
                )
        else:
            insights.append(
                {
                    "source_metric": "rows",
                    "value": int(len(df)),
                    "unit": "count",
                    "category": "dataset",
                    "text": f"The dataset contains {len(df)} rows and {len(df.columns)} columns ready for analysis.",
                    "evidence_ref": "dataset",
                    "status": "neutral",
                }
            )

    return insights


def generate_recommendations(issues: Iterable[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    """Translate quality issues into actionable recommendations."""
    if issues is None:
        return []

    ordered_issues = _sort_issues_by_severity(list(issues))
    if not ordered_issues:
        return [
            {
                "type": "monitoring",
                "severity": "LOW",
                "priority": "low",
                "text": "No immediate issues require intervention. Continue periodic monitoring for drift or new anomalies.",
            }
        ]

    recommendations: List[Dict[str, Any]] = []
    for issue in ordered_issues:
        issue_type = str(issue.get("type", "general")).lower()
        column = str(issue.get("column", "dataset"))
        severity = str(issue.get("severity", "MEDIUM")).upper()
        pct = float(issue.get("affected_pct", 0.0) or 0.0)

        if issue_type == "missing_values":
            text = f"Fill or remove missing values in {column} before using it in KPIs or segment analyses."
        elif issue_type == "duplicate_rows":
            text = "Deduplicate repeated rows before calculating revenue totals or customer-level metrics."
        elif issue_type in {"outliers", "negative_values"}:
            text = f"Review extreme or invalid values in {column}; validate whether they represent legitimate events or data-entry errors."
        elif issue_type == "duplicate_ids":
            text = f"Investigate duplicate identifiers in {column} to confirm whether records should be merged or cleaned."
        elif issue_type == "inconsistent_format":
            text = f"Standardize the format of {column} so grouping, filtering, and joins remain consistent."
        elif issue_type == "mixed_types":
            text = f"Normalize {column} into a single value type to avoid inconsistent model input or downstream filters."
        else:
            text = issue.get("suggested_action") or f"Review {column} and confirm whether the data quality issue requires a remediation step."

        if pct > 0:
            text = f"{text} Current impact: {pct:.1f}% of rows are affected."

        recommendations.append(
            {
                "type": issue_type,
                "column": column,
                "severity": severity,
                "priority": severity.lower(),
                "text": text,
            }
        )

    return recommendations


def build_dashboard_summary(
    df: pd.DataFrame,
    quality_result: Dict[str, Any] | None = None,
    insights: List[Dict[str, Any]] | None = None,
    recommendations: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Return a compact dashboard summary for the active dataset."""
    if df is None or df.empty:
        return {
            "quality_score": 100.0,
            "grade": "Excellent",
            "rows": 0,
            "cols": 0,
            "insights": [],
            "recommendations": [],
            "status": "empty",
        }

    if quality_result is None:
        try:
            from core.quality import analyze_quality

            quality_result = analyze_quality(df)
        except Exception:
            quality_result = {"overall_score": 100.0, "grade": "Excellent", "issues": []}

    quality_score = float(quality_result.get("overall_score", 100.0))
    grade = str(quality_result.get("grade", "Excellent"))
    issues = _build_issue_summary(quality_result)

    summary_insights = insights or generate_insights(df, quality_result)
    summary_recommendations = recommendations or generate_recommendations(issues)

    if quality_score >= 85:
        status = "healthy"
    elif quality_score >= 65:
        status = "watchlist"
    else:
        status = "needs_attention"

    return {
        "quality_score": round(quality_score, 1),
        "grade": grade,
        "rows": int(len(df)),
        "cols": int(len(df.columns)),
        "insights": summary_insights,
        "recommendations": summary_recommendations,
        "status": status,
    }


__all__ = ["generate_insights", "generate_recommendations", "build_dashboard_summary"]
