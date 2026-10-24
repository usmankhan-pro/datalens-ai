"""Goal-aware readiness verdict evaluation engine for DataLens AI.

Evaluates cleaned data against the user's declared analytical goal (ML, Reporting,
Research, Business Analysis) using a deterministic pass/warn/fail checklist.
All items contain explainable reasons, remaining actions, and an explicit
decision-support disclaimer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from core.cleaning.pipeline import detect_outliers_iqr
from core.context.models import UserContext

DISCLAIMER_TEXT = (
    "Disclaimer: Readiness verdicts and quality scores are rule-based decision support indicators, "
    "not mathematical proof of dataset fitness or model performance. Always verify critical business logic "
    "and conduct application-specific validation before deployment."
)


@dataclass
class VerdictItem:
    """A single criterion checklist item."""
    name: str
    status: str  # 'PASS', 'WARN', 'FAIL'
    metric_value: str
    reason: str
    remaining_action: Optional[str] = None


@dataclass
class ReadinessVerdict:
    """Overall readiness verdict container."""
    goal: str
    overall_status: str  # 'PASS', 'WARN', 'FAIL'
    readiness_score: float  # 0 to 100
    total_checks: int
    passed_checks: int
    warn_checks: int
    failed_checks: int
    items: List[VerdictItem] = field(default_factory=list)
    disclaimer: str = DISCLAIMER_TEXT


def evaluate_readiness(
    df: pd.DataFrame,
    context: Optional[UserContext] = None,
) -> ReadinessVerdict:
    """
    Evaluate dataset readiness against the user's analytical goal.

    Args:
        df: The working/cleaned DataFrame.
        context: UserContext with stated goal and optional target column.

    Returns:
        ReadinessVerdict with detailed pass/warn/fail checklist.
    """
    if df is None or df.empty:
        return ReadinessVerdict(
            goal="general",
            overall_status="FAIL",
            readiness_score=0.0,
            total_checks=1,
            passed_checks=0,
            warn_checks=0,
            failed_checks=1,
            items=[
                VerdictItem(
                    name="Data Availability",
                    status="FAIL",
                    metric_value="0 rows",
                    reason="Dataset contains 0 rows or is empty.",
                    remaining_action="Upload a populated dataset.",
                )
            ],
        )

    ctx = context or UserContext()
    goal = ctx.goal.lower()
    target_col = ctx.target_column

    total_rows = len(df)
    total_cells = int(df.size)
    missing_cells = int(df.isna().sum().sum())
    missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
    duplicates = int(df.duplicated().sum())
    dup_pct = (duplicates / total_rows * 100.0) if total_rows > 0 else 0.0

    items: List[VerdictItem] = []

    # ---------------------------------------------------------
    # Evaluation Logic Branch by Goal
    # ---------------------------------------------------------

    if goal in ("ml", "machine_learning"):
        # Check 1: Missing feature tolerance
        if missing_pct == 0.0:
            items.append(VerdictItem("Feature Completeness", "PASS", "0.0% missing", "All features are completely non-null."))
        elif missing_pct <= 2.0:
            items.append(VerdictItem("Feature Completeness", "WARN", f"{missing_pct:.2f}% missing", "Minor missingness present.", "Impute missing values in the Clean workspace."))
        else:
            items.append(VerdictItem("Feature Completeness", "FAIL", f"{missing_pct:.2f}% missing", "High missingness causes model inference failures.", "Impute or drop sparse columns before training."))

        # Check 2: Target Variable Health
        if target_col and target_col in df.columns:
            target_series = df[target_col]
            t_missing = int(target_series.isna().sum())
            if t_missing == 0:
                items.append(VerdictItem("Target Label Completeness", "PASS", "100% labeled", f"Target '{target_col}' has zero missing values."))
            else:
                items.append(VerdictItem("Target Label Completeness", "FAIL", f"{t_missing} unlabeled rows", f"Supervised models cannot train on unlabeled instances in '{target_col}'.", f"Filter out rows missing '{target_col}'."))

            # Target class imbalance
            if not pd.api.types.is_numeric_dtype(target_series) or target_series.nunique() <= 10:
                counts = target_series.value_counts()
                if len(counts) >= 2:
                    ratio = counts.iloc[0] / max(1, counts.iloc[-1])
                    if ratio <= 3.0:
                        items.append(VerdictItem("Class Balance", "PASS", f"{ratio:.1f}:1 ratio", "Class distribution is sufficiently balanced."))
                    elif ratio <= 8.0:
                        items.append(VerdictItem("Class Balance", "WARN", f"{ratio:.1f}:1 ratio", "Moderate class imbalance detected.", "Consider SMOTE, class weights, or stratified sampling."))
                    else:
                        items.append(VerdictItem("Class Balance", "FAIL", f"{ratio:.1f}:1 ratio", "Severe class imbalance may cause model to predict majority class only.", "Resample training set or use cost-sensitive loss."))
        else:
            items.append(VerdictItem("Target Variable Specification", "WARN", "Not specified", "No target feature designated for supervised learning evaluation.", "Select a target column in Context Intake."))

        # Check 3: Duplicates & Leakage
        if duplicates == 0:
            items.append(VerdictItem("Data Leakage & Duplication", "PASS", "0 duplicates", "No duplicate rows found."))
        else:
            items.append(VerdictItem("Data Leakage & Duplication", "FAIL", f"{duplicates:,} duplicate rows ({dup_pct:.1f}%)", "Duplicate rows cause test leakage between CV folds.", "Apply deduplication in Clean workspace."))

        # Check 4: Identifier / High Cardinality Features
        leakage_cols = []
        for col in df.columns:
            if col != target_col:
                if any(id_hint in col.lower() for id_hint in ["id", "uuid", "key", "token"]):
                    if df[col].nunique() / total_rows >= 0.8:
                        leakage_cols.append(col)
        if not leakage_cols:
            items.append(VerdictItem("Identifier Feature Hygiene", "PASS", "No leaky IDs", "No high-uniqueness identifier columns detected."))
        else:
            items.append(VerdictItem("Identifier Feature Hygiene", "WARN", f"{len(leakage_cols)} ID column(s)", f"Columns ({', '.join(leakage_cols[:3])}) may induce overfitting.", "Drop identifier features prior to training."))

        # Check 5: Sample Size
        if total_rows >= 100:
            items.append(VerdictItem("Sample Size Adequacy", "PASS", f"{total_rows:,} rows", "Sufficient observations for train/validation splits."))
        elif total_rows >= 30:
            items.append(VerdictItem("Sample Size Adequacy", "WARN", f"{total_rows:,} rows", "Limited sample size; risk of high validation variance.", "Collect more records if possible."))
        else:
            items.append(VerdictItem("Sample Size Adequacy", "FAIL", f"{total_rows:,} rows", "Critically small dataset (<30 rows) for machine learning.", "Expand training corpus."))

    elif goal in ("reporting", "kpi_reporting"):
        # Check 1: Duplicate elimination
        if duplicates == 0:
            items.append(VerdictItem("Revenue / KPI Uniqueness", "PASS", "0 duplicates", "No duplicate rows; aggregations will not double-count."))
        elif dup_pct < 1.0:
            items.append(VerdictItem("Revenue / KPI Uniqueness", "WARN", f"{duplicates:,} duplicates ({dup_pct:.1f}%)", "Minor duplicates found.", "Remove duplicates in Clean workspace."))
        else:
            items.append(VerdictItem("Revenue / KPI Uniqueness", "FAIL", f"{duplicates:,} duplicates ({dup_pct:.1f}%)", "High duplicate count will corrupt aggregated KPI figures.", "Deduplicate dataset before reporting."))

        # Check 2: Date Dimension
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        if date_cols:
            items.append(VerdictItem("Temporal Dimension", "PASS", f"{len(date_cols)} datetime column(s)", f"Valid temporal columns found: {', '.join(date_cols)}."))
        else:
            items.append(VerdictItem("Temporal Dimension", "WARN", "No datetime column", "No native datetime column found; periodic trend reporting disabled.", "Parse date text columns in Clean workspace."))

        # Check 3: Missing KPI values
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
        num_missing = sum(int(df[c].isna().sum()) for c in num_cols)
        if num_missing == 0:
            items.append(VerdictItem("Numeric Metric Completeness", "PASS", "0 nulls in KPIs", "All numeric KPI columns are complete."))
        else:
            items.append(VerdictItem("Numeric Metric Completeness", "WARN", f"{num_missing:,} missing cells", "Missing values in KPI columns may distort SUM/AVG totals.", "Impute with 0 or group medians."))

        # Check 4: Header standardization
        non_snake = [c for c in df.columns if " " in str(c) or not str(c).islower()]
        if not non_snake:
            items.append(VerdictItem("Header Uniformity", "PASS", "Clean snake_case", "Column headers conform to standard naming."))
        else:
            items.append(VerdictItem("Header Uniformity", "WARN", f"{len(non_snake)} non-standard names", "Columns contain spaces or mixed casing.", "Standardize headers in Clean workspace."))

    else:
        # Business Analysis, Research, General
        if missing_pct <= 1.0:
            items.append(VerdictItem("Data Completeness", "PASS", f"{missing_pct:.1f}% missing", "High completeness across all dimensions."))
        elif missing_pct <= 10.0:
            items.append(VerdictItem("Data Completeness", "WARN", f"{missing_pct:.1f}% missing", "Moderate missingness; verify MAR/MCAR assumptions.", "Impute missing values."))
        else:
            items.append(VerdictItem("Data Completeness", "FAIL", f"{missing_pct:.1f}% missing", "Excessive missingness may bias statistical inferences.", "Filter or impute critical columns."))

        if total_rows >= 30:
            items.append(VerdictItem("Statistical Power (Sample Size)", "PASS", f"n = {total_rows:,}", "Sample size meets Central Limit Theorem threshold (n >= 30)."))
        else:
            items.append(VerdictItem("Statistical Power (Sample Size)", "WARN", f"n = {total_rows:,}", "Small sample size (n < 30); use non-parametric tests.", "Acquire additional observations."))

        if duplicates == 0:
            items.append(VerdictItem("Observation Uniqueness", "PASS", "0 duplicates", "All observations are unique."))
        else:
            items.append(VerdictItem("Observation Uniqueness", "WARN", f"{duplicates:,} duplicate rows", "Duplicate observations detected.", "Review and remove duplicate records."))

        # Outlier exposure
        num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
        outlier_total = sum(int(detect_outliers_iqr(df[c]).sum()) for c in num_cols)
        outlier_pct = (outlier_total / max(1, total_rows * len(num_cols))) * 100.0 if num_cols else 0.0
        if outlier_pct <= 3.0:
            items.append(VerdictItem("Outlier Exposure", "PASS", f"{outlier_pct:.1f}% outliers", "Low outlier contamination."))
        else:
            items.append(VerdictItem("Outlier Exposure", "WARN", f"{outlier_pct:.1f}% outliers", "High proportion of extreme values may distort means.", "Review outlier treatment in Clean workspace."))

    # ---------------------------------------------------------
    # Overall Status & Score
    # ---------------------------------------------------------
    total_cnt = len(items)
    passed_cnt = sum(1 for it in items if it.status == "PASS")
    warn_cnt = sum(1 for it in items if it.status == "WARN")
    failed_cnt = sum(1 for it in items if it.status == "FAIL")

    if failed_cnt > 0:
        overall_status = "FAIL"
    elif warn_cnt > 0:
        overall_status = "WARN"
    else:
        overall_status = "PASS"

    # Score calculation: 100 points max, -20 per FAIL, -8 per WARN
    raw_score = 100.0 - (failed_cnt * 20.0) - (warn_cnt * 8.0)
    readiness_score = float(max(0.0, min(100.0, raw_score)))

    return ReadinessVerdict(
        goal=goal,
        overall_status=overall_status,
        readiness_score=round(readiness_score, 1),
        total_checks=total_cnt,
        passed_checks=passed_cnt,
        warn_checks=warn_cnt,
        failed_checks=failed_cnt,
        items=items,
    )
