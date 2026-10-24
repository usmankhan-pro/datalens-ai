"""Goal-aware action planner for DataLens AI.

Maps detected data quality issues and analytical goals (ML, Reporting, Research, etc.)
into an ordered, explainable action plan.
Every planned action includes:
- What (title and operation)
- Why (analytical justification)
- Severity ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')
- Risk label ('safe', 'review', 'risky')
- Quality-score impact computed directly by executing the transformation on a DataFrame copy.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from core.cleaning.pipeline import (
    CLEANING_STAGES,
    OPERATION_SPECS,
    apply_operation,
    detect_outliers_iqr,
)
from core.context.models import UserContext
from core.quality.score import analyze_quality


@dataclass
class PlannedAction:
    """A single recommended action within the Action Plan."""
    step_number: int
    operation: str
    stage: str
    title: str
    reason: str
    severity: str
    risk: str
    params: Dict[str, Any]
    columns: List[str]
    score_impact: float


@dataclass
class ActionPlan:
    """Ordered collection of goal-aware cleaning and preparation actions."""
    goal: str
    domain: str
    target_column: Optional[str]
    initial_quality_score: float
    potential_quality_score: float
    actions: List[PlannedAction] = field(default_factory=list)

    def safe_actions(self) -> List[PlannedAction]:
        """Return only actions labeled as 'safe'."""
        return [a for a in self.actions if a.risk == "safe"]

    def risky_actions(self) -> List[PlannedAction]:
        """Return actions requiring explicit user review or approval."""
        return [a for a in self.actions if a.risk in ("review", "risky")]


def create_action_plan(
    df: pd.DataFrame,
    context: Optional[UserContext] = None,
) -> ActionPlan:
    """
    Generate an ordered, goal-aware action plan for a DataFrame.

    Args:
        df: The target raw or working DataFrame.
        context: Optional user context containing goal, target column, domain.

    Returns:
        ActionPlan with ordered PlannedActions and computed score impacts.
    """
    if df is None or df.empty:
        return ActionPlan(
            goal="general",
            domain="General",
            target_column=None,
            initial_quality_score=100.0,
            potential_quality_score=100.0,
            actions=[],
        )

    ctx = context or UserContext()
    goal = ctx.goal.lower()
    target_col = ctx.target_column
    domain = ctx.domain

    initial_quality = float(analyze_quality(df).get("overall_score", 100.0))

    candidate_steps: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # 1. Structural Checks
    # -------------------------------------------------------------
    # Empty rows
    empty_rows_cnt = int(df.isna().all(axis=1).sum())
    if empty_rows_cnt > 0:
        candidate_steps.append({
            "operation": "drop_empty_rows",
            "stage": "structure",
            "title": f"Drop {empty_rows_cnt:,} completely empty rows",
            "reason": "Completely blank rows distort record counts and induce artificial nulls.",
            "severity": "HIGH",
            "risk": "safe",
            "params": {"how": "all"},
            "columns": list(df.columns),
        })

    # Empty columns
    empty_cols = [c for c in df.columns if df[c].isna().all()]
    if empty_cols:
        candidate_steps.append({
            "operation": "drop_empty_columns",
            "stage": "structure",
            "title": f"Drop {len(empty_cols)} empty column(s) ({', '.join(empty_cols)})",
            "reason": "Columns with 100% missing values provide zero analytical value.",
            "severity": "HIGH",
            "risk": "safe",
            "params": {},
            "columns": empty_cols,
        })

    # Column name snake_casing
    unnormalized_cols = [c for c in df.columns if " " in str(c) or "-" in str(c) or not str(c).islower()]
    if len(unnormalized_cols) > 0:
        candidate_steps.append({
            "operation": "snake_case_columns",
            "stage": "structure",
            "title": "Standardize column headers to snake_case",
            "reason": "Prevents syntax errors and whitespace mismatches across downstream scripts.",
            "severity": "LOW",
            "risk": "safe",
            "params": {},
            "columns": unnormalized_cols,
        })

    # -------------------------------------------------------------
    # 2. Placeholders & Invalid Values
    # -------------------------------------------------------------
    str_cols = [c for c in df.columns if df[c].dtype == "object" or pd.api.types.is_string_dtype(df[c])]
    has_sentinels = False
    for c in str_cols:
        sample_str = df[c].dropna().astype(str).str.strip().str.lower()
        if sample_str.isin(["n/a", "na", "-", "null", "none", "999", "?"]).any():
            has_sentinels = True
            break
    if has_sentinels:
        candidate_steps.append({
            "operation": "replace_placeholders",
            "stage": "invalid_values",
            "title": "Convert text placeholders ('N/A', '-', '999') to NaN",
            "reason": "Sentinel strings mask missingness and corrupt numerical statistics.",
            "severity": "HIGH",
            "risk": "safe",
            "params": {},
            "columns": str_cols,
        })

    # -------------------------------------------------------------
    # 3. Type Conversion Checks
    # -------------------------------------------------------------
    num_text_cols = []
    for c in str_cols:
        sample = df[c].dropna().astype(str).head(30)
        if sample.str.contains(r"[\$,%]|^\s*\([0-9\.]+\)\s*$", regex=True).any():
            num_text_cols.append(c)

    if num_text_cols:
        candidate_steps.append({
            "operation": "convert_numeric_text",
            "stage": "types",
            "title": f"Cast formatted currency/percentage strings to numeric ({', '.join(num_text_cols)})",
            "reason": "Allows mathematical operations, aggregations, and ML feature extraction.",
            "severity": "HIGH",
            "risk": "safe",
            "params": {"columns": num_text_cols},
            "columns": num_text_cols,
        })

    # Date parsing
    date_candidate_cols = []
    for c in str_cols:
        if any(h in c.lower() for h in ["date", "time", "day", "created", "updated"]):
            date_candidate_cols.append(c)
    if date_candidate_cols:
        candidate_steps.append({
            "operation": "parse_dates",
            "stage": "types",
            "title": f"Parse date string columns into datetime ({', '.join(date_candidate_cols)})",
            "reason": "Crucial for time-series trend analysis, cohort tracking, and date math.",
            "severity": "HIGH" if goal == "reporting" else "MEDIUM",
            "risk": "safe",
            "params": {"columns": date_candidate_cols},
            "columns": date_candidate_cols,
        })

    # Text Standardization
    if str_cols:
        candidate_steps.append({
            "operation": "standardize_text",
            "stage": "text",
            "title": "Strip leading/trailing whitespace from string columns",
            "reason": "Accidental spaces create split categories in GROUP BY and cardinality explosion.",
            "severity": "MEDIUM",
            "risk": "safe",
            "params": {"strip": True, "case": "preserve"},
            "columns": str_cols,
        })

    # -------------------------------------------------------------
    # 4. Duplicates
    # -------------------------------------------------------------
    dup_cnt = int(df.duplicated().sum())
    if dup_cnt > 0:
        sev = "CRITICAL" if goal in ("ml", "reporting") else "HIGH"
        candidate_steps.append({
            "operation": "remove_duplicates",
            "stage": "duplicates",
            "title": f"Deduplicate {dup_cnt:,} identical rows",
            "reason": (
                "For ML: prevents data leakage between train/test splits. "
                "For Reporting: eliminates double-counting revenue and metrics."
            ),
            "severity": sev,
            "risk": "safe",
            "params": {"keep": "first"},
            "columns": list(df.columns),
        })

    # -------------------------------------------------------------
    # 5. Missing Values & Goal-Specific Strategies
    # -------------------------------------------------------------
    missing_cols = [c for c in df.columns if df[c].isna().sum() > 0]
    num_missing = [c for c in missing_cols if pd.api.types.is_numeric_dtype(df[c])]
    cat_missing = [c for c in missing_cols if c not in num_missing]

    # Extreme missing columns (> 50%)
    heavy_missing_cols = [c for c in df.columns if df[c].isna().mean() > 0.5]
    if heavy_missing_cols:
        candidate_steps.append({
            "operation": "drop_missing_columns",
            "stage": "missing_values",
            "title": f"Drop columns with >50% missing values ({', '.join(heavy_missing_cols)})",
            "reason": "Features missing over half their records often degrade statistical signal.",
            "severity": "HIGH",
            "risk": "risky",
            "params": {"threshold_pct": 50.0},
            "columns": heavy_missing_cols,
        })

    if num_missing:
        strat = "median" if goal in ("ml", "research") else "mean"
        candidate_steps.append({
            "operation": "fill_missing_numeric",
            "stage": "missing_values",
            "title": f"Impute missing numeric values using {strat} ({', '.join(num_missing[:4])})",
            "reason": "Statistical models cannot process NaN values; median preserves robust central tendency.",
            "severity": "HIGH" if goal == "ml" else "MEDIUM",
            "risk": "review",
            "params": {"method": strat, "columns": num_missing},
            "columns": num_missing,
        })

    if cat_missing:
        strat = "mode" if goal == "ml" else "constant"
        candidate_steps.append({
            "operation": "fill_missing_categorical",
            "stage": "missing_values",
            "title": f"Impute missing categorical fields using {strat} ({', '.join(cat_missing[:4])})",
            "reason": "Avoids dropped rows while maintaining distinct representation of missingness.",
            "severity": "MEDIUM",
            "risk": "review",
            "params": {"method": strat, "columns": cat_missing},
            "columns": cat_missing,
        })

    # -------------------------------------------------------------
    # 6. Outlier Treatment (Flagged by default; cap/remove only on approval)
    # -------------------------------------------------------------
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    outlier_cols = []
    for c in num_cols:
        mask = detect_outliers_iqr(df[c], factor=1.5)
        if mask.sum() > 0:
            outlier_cols.append(c)

    if outlier_cols:
        candidate_steps.append({
            "operation": "cap_outliers",
            "stage": "outliers",
            "title": f"Cap extreme outliers using IQR fences ({', '.join(outlier_cols[:4])})",
            "reason": (
                "Extreme outliers skew linear coefficients and gradient descent. "
                "Capping (Winsorizing) preserves sample size without destabilizing variance."
            ),
            "severity": "HIGH" if goal == "ml" else "LOW",
            "risk": "risky",
            "params": {"columns": outlier_cols, "factor": 1.5},
            "columns": outlier_cols,
        })

    # -------------------------------------------------------------
    # Compute Exact Quality Score Impact on DataFrame Copy
    # -------------------------------------------------------------
    planned_actions: List[PlannedAction] = []
    cumulative_df = df.copy()

    for idx, step_spec in enumerate(candidate_steps, start=1):
        op = step_spec["operation"]
        params = step_spec["params"]

        # Run step on copy to measure quality score delta
        try:
            res = apply_operation(cumulative_df.copy(), op, params)
            test_df = res["df"]
            new_quality = float(analyze_quality(test_df).get("overall_score", initial_quality))
            score_delta = round(new_quality - initial_quality, 1)
        except Exception:
            score_delta = 0.0

        planned_actions.append(
            PlannedAction(
                step_number=idx,
                operation=op,
                stage=step_spec["stage"],
                title=step_spec["title"],
                reason=step_spec["reason"],
                severity=step_spec["severity"],
                risk=step_spec["risk"],
                params=params,
                columns=step_spec["columns"],
                score_impact=score_delta,
            )
        )

    # Calculate potential score if all safe actions are applied
    simulated_df = df.copy()
    for act in planned_actions:
        if act.risk == "safe":
            try:
                r = apply_operation(simulated_df, act.operation, act.params)
                simulated_df = r["df"]
            except Exception:
                pass
    potential_quality = float(analyze_quality(simulated_df).get("overall_score", initial_quality))

    return ActionPlan(
        goal=goal,
        domain=domain,
        target_column=target_col,
        initial_quality_score=round(initial_quality, 1),
        potential_quality_score=round(potential_quality, 1),
        actions=planned_actions,
    )
