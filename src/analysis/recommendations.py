"""Insights and recommendations engine based on calculated statistics.

Each insight is an observed fact with supporting values, a rationale,
a recommended next step, and limitations.  No LLM or fabricated content.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.analysis.descriptive import column_profile
from src.quality.quality_score import compute_quality_score


@staticmethod
def _pct(n: int, d: int) -> float:
    return round(n / d * 100, 2) if d > 0 else 0.0


def generate_insights(data: pd.DataFrame, quality_result=None) -> list[dict[str, Any]]:
    """Generate evidence-backed insights from the dataset.

    Returns a list of dicts with keys: category, title, observation,
    evidence, why_it_matters, recommended_action, limitation.
    """
    n_rows, n_cols = data.shape
    insights: list[dict[str, Any]] = []

    if quality_result is None:
        quality_result = compute_quality_score(data)

    # ---- 1. Overall quality ----
    insights.append({
        "category": "Observed fact",
        "title": "Dataset quality score",
        "observation": f"Overall quality score is {quality_result.overall_score}/100 ({quality_result.overall_label}).",
        "evidence": f"Computed from {n_rows} rows and {n_cols} columns across five dimensions.",
        "why_it_matters": "A low score indicates issues that may affect analysis reliability.",
        "recommended_action": "Review dimension details and address HIGH-severity issues first.",
        "limitation": "The score does not measure accuracy, bias, or fitness for a specific objective.",
    })

    # ---- 2. Missing values ----
    missing_report: dict[str, dict[str, Any]] = {}
    for col in data.columns:
        n_missing = int(data[col].isna().sum())
        if n_missing > 0:
            missing_report[str(col)] = {
                "n_missing": n_missing,
                "pct": _pct(n_missing, n_rows),
            }

    if missing_report:
        worst_col = max(missing_report, key=lambda c: missing_report[c]["n_missing"])
        worst = missing_report[worst_col]
        insights.append({
            "category": "Observed fact",
            "title": "High missingness in a column",
            "observation": f"'{worst_col}' has {worst['n_missing']:,} missing values ({worst['pct']}% of rows).",
            "evidence": f"{len(missing_report)} column(s) have missing values.",
            "why_it_matters": "Missing values can bias analysis and reduce effective sample size.",
            "recommended_action": "Review the column and choose imputation or row removal in the Cleaning Studio.",
            "limitation": "Missingness may be systematic (e.g. skip-logic in surveys), not random.",
        })
    else:
        insights.append({
            "category": "Observed fact",
            "title": "No missing values",
            "observation": "No missing values detected in any column.",
            "evidence": f"All {n_rows * n_cols} cells are populated.",
            "why_it_matters": "No imputation or row removal is needed for missingness.",
            "recommended_action": "Proceed to analysis without missing-value handling.",
            "limitation": "Blank strings or placeholders may not be flagged as missing unless normalized.",
        })

    # ---- 3. Duplicate rows ----
    n_duplicates = int(data.duplicated().sum())
    if n_duplicates > 0:
        insights.append({
            "category": "Observed fact",
            "title": "Duplicate rows detected",
            "observation": f"{n_duplicates} exact duplicate rows ({_pct(n_duplicates, n_rows)}% of dataset).",
            "evidence": f"{n_rows - n_duplicates} unique rows out of {n_rows} total.",
            "why_it_matters": "Duplicates can inflate counts and bias models.",
            "recommended_action": "Review duplicates and remove exact copies in the Cleaning Studio.",
            "limitation": "Only exact row duplicates are detected; near-duplicates are not flagged.",
        })

    # ---- 4. Constant columns ----
    constant_cols = [
        str(col) for col in data.columns
        if not data[col].isna().all() and data[col].nunique(dropna=True) <= 1
    ]
    if constant_cols:
        insights.append({
            "category": "Observed fact",
            "title": "Constant column(s)",
            "observation": f"{len(constant_cols)} column(s) contain only one distinct value: {', '.join(constant_cols)}.",
            "evidence": "Each flagged column has n_unique = 1 among non-null values.",
            "why_it_matters": "Constant columns carry no discriminating information for modeling.",
            "recommended_action": "Consider dropping constant columns before analysis.",
            "limitation": "A constant may be intentional (e.g. a fixed treatment flag).",
        })

    # ---- 5. Numeric-as-text ----
    text_numeric = []
    for col in data.select_dtypes(include=["object", "string"]).columns:
        series = data[col].dropna()
        if series.empty:
            continue
        converted = pd.to_numeric(series.astype(str).head(500), errors="coerce")
        if converted.notna().mean() >= 0.8:
            text_numeric.append(str(col))
    if text_numeric:
        insights.append({
            "category": "Observed fact",
            "title": "Numeric values stored as text",
            "observation": f"{len(text_numeric)} column(s) store numbers as text: {', '.join(text_numeric)}.",
            "evidence": "Most non-null values in these columns parse successfully as numbers.",
            "why_it_matters": "Text-stored numbers cannot be used in numeric analysis or correlation.",
            "recommended_action": "Convert to numeric using 'Fix types' in the Cleaning Studio.",
            "limitation": "Values that cannot parse will become missing.",
        })

    # ---- 6. Strongest correlation ----
    numeric_cols = data.select_dtypes(include="number").columns.tolist()
    if len(numeric_cols) >= 2:
        from src.analysis.correlation import strong_correlations
        strong = strong_correlations(data, threshold=0.7)
        if strong:
            top = strong[0]
            insights.append({
                "category": "Statistical interpretation",
                "title": "Strong numeric association",
                "observation": f"'{top['column_a']}' and '{top['column_b']}' are correlated (r = {top['correlation']}, n = {top['n_samples']}).",
                "evidence": f"|r| = {abs(top['correlation'])} based on {top['n_samples']} complete pairs.",
                "why_it_matters": "Strong associations may indicate redundancy or a meaningful relationship.",
                "recommended_action": "Inspect with a scatter plot before drawing conclusions.",
                "limitation": "Correlation does not imply causation and may be driven by outliers.",
            })

    # ---- 7. High cardinality ----
    high_card = []
    for col in data.select_dtypes(include=["object", "string"]).columns:
        series = data[col].dropna()
        if series.empty:
            continue
        n_unique = int(series.nunique())
        if n_rows > 10 and n_unique > 10 and n_unique / len(series) >= 0.9:
            high_card.append((str(col), n_unique))
    if high_card:
        cols_str = ", ".join(f"{c} ({n} unique)" for c, n in high_card)
        insights.append({
            "category": "Observed fact",
            "title": "High-cardinality text column(s)",
            "observation": f"{len(high_card)} column(s) have nearly all unique values: {cols_str}.",
            "evidence": "Unique-value ratio >= 90% of non-null rows.",
            "why_it_matters": "High-cardinality columns are often identifiers, not useful for aggregation.",
            "recommended_action": "Treat as identifiers; do not include in default correlation or grouping.",
            "limitation": "Some high-cardinality columns (e.g. product SKUs) are meaningful identifiers.",
        })

    return insights


def recommendations_for_cleaning(
    data: pd.DataFrame,
    quality_result=None,
) -> list[dict[str, Any]]:
    """Return prioritized cleaning recommendations."""
    if quality_result is None:
        quality_result = compute_quality_score(data)

    recs: list[dict[str, Any]] = []

    # Prioritize HIGH severity dimension recommendations
    for dim in quality_result.dimensions:
        if dim.severity == "HIGH" and dim.score is not None and dim.score < 100:
            recs.append({
                "priority": "HIGH",
                "dimension": dim.name,
                "action": dim.recommended_action,
                "effect_on_score": dim.effect_on_overall,
                "issue": "; ".join(dim.issues)[:200],
            })
        elif dim.severity == "MEDIUM" and dim.score is not None and dim.score < 100:
            recs.append({
                "priority": "MEDIUM",
                "dimension": dim.name,
                "action": dim.recommended_action,
                "effect_on_score": dim.effect_on_overall,
                "issue": "; ".join(dim.issues)[:200],
            })

    # Sort: HIGH first, then MEDIUM
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}
    recs.sort(key=lambda r: order.get(r["priority"], 99))

    return recs
