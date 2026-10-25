"""Dataset quality scoring engine.

Produces a reproducible 0-100 quality score from five measured dimensions:
completeness, validity, consistency, uniqueness, and structural quality.

Each dimension is scored independently from measured properties of the
dataset.  Dimension scores are combined using configurable weights from
config.settings.  A dimension that cannot be assessed is excluded from
the weighted average and its limitation is reported.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config.settings import (
    CARDINALITY_THRESHOLDS,
    DUPLICATE_THRESHOLDS,
    MISSING_THRESHOLDS,
    QUALITY_THRESHOLDS,
    QUALITY_WEIGHTS,
    SCORE_INTERPRETATIONS,
    IDENTIFIER_NAME_HINTS,
)


@dataclass(frozen=True)
class DimensionResult:
    """Result for one quality dimension."""

    name: str
    weight: int
    score: float | None
    issues: list[str]
    numerator: float | int | None
    denominator: float | int | None
    severity: str
    effect_on_overall: float
    recommended_action: str
    limitation: str


@dataclass(frozen=True)
class QualityScoreResult:
    """Complete quality assessment result."""

    overall_score: float
    overall_label: str
    overall_interpretation: str
    overall_recommendation: str
    dimensions: list[DimensionResult]
    excluded_dimensions: list[str]
    n_rows: int
    n_cols: int
    computed_from: str


def _safe_divide(numerator: float | int, denominator: float | int) -> float | None:
    """Divide safely, returning None when the denominator is zero or missing."""
    if denominator is None or denominator == 0:
        return None
    try:
        value = float(numerator) / float(denominator) * 100.0
        return round(max(0.0, min(100.0, value)), 2)
    except (TypeError, ValueError):
        return None


def _severity_from_pct(pct: float) -> str:
    """Map a percentage to a severity label."""
    if pct >= 50.0:
        return "HIGH"
    if pct >= 20.0:
        return "MEDIUM"
    if pct > 0.0:
        return "LOW"
    return "NONE"


def _is_identifier_column(name: str) -> bool:
    """Heuristic: does the column name suggest an identifier?"""
    return any(hint in name.casefold() for hint in IDENTIFIER_NAME_HINTS)


def _completeness_score(data: pd.DataFrame) -> DimensionResult:
    """Score completeness based on missing-cell percentage."""

    n_rows, n_cols = data.shape
    total_cells = n_rows * n_cols
    missing_cells = int(data.isna().sum().sum())

    if total_cells == 0:
        return DimensionResult(
            name="Completeness",
            weight=QUALITY_WEIGHTS.completeness,
            score=None,
            issues=["Dataset has no cells to assess."],
            numerator=0,
            denominator=0,
            severity="INFO",
            effect_on_overall=0.0,
            recommended_action="Upload a dataset with data.",
            limitation="Cannot assess completeness of an empty dataset.",
        )

    present_cells = total_cells - missing_cells
    score = round(present_cells / total_cells * 100.0, 2)
    pct_missing = round(missing_cells / total_cells * 100.0, 2)

    issues: list[str] = []
    if missing_cells > 0:
        issues.append(f"{missing_cells:,} of {total_cells:,} cells are missing ({pct_missing}%).")
    else:
        issues.append("No missing cells detected.")

    severity = _severity_from_pct(pct_missing)
    action = (
        "No action needed."
        if severity == "NONE"
        else "Impute or drop missing values in the Cleaning Studio."
    )
    limitation = (
        "Counts blank strings and configured placeholders as missing only if "
        "they were normalized during loading; otherwise treats them as present."
    )

    return DimensionResult(
        name="Completeness",
        weight=QUALITY_WEIGHTS.completeness,
        score=score,
        issues=issues,
        numerator=present_cells,
        denominator=total_cells,
        severity=severity,
        effect_on_overall=round(score * QUALITY_WEIGHTS.completeness / 100.0, 2),
        recommended_action=action,
        limitation=limitation,
    )


def _validity_score(data: pd.DataFrame) -> DimensionResult:
    """Score validity based on values stored in the wrong type (e.g. numbers as text)."""

    n_rows, _ = data.shape
    text_columns = data.select_dtypes(include=["object", "string", "str"]).columns

    invalid_columns = 0
    details: list[str] = []
    for col in text_columns:
        series = data[col].dropna()
        if series.empty:
            continue
        sample = series.astype(str).head(500)
        converted = pd.to_numeric(sample, errors="coerce")
        numeric_rate = converted.notna().mean()
        if numeric_rate >= 0.8:
            invalid_columns += 1
            details.append(f"'{col}' stores {numeric_rate:.0%} numeric values as text.")
        else:
            parsed = pd.to_datetime(sample, errors="coerce", format="mixed")
            date_rate = parsed.notna().mean()
            if date_rate >= 0.9:
                invalid_columns += 1
                details.append(f"'{col}' stores {date_rate:.0%} date-like values as text.")

    total_text_cols = len(text_columns)
    if total_text_cols == 0:
        return DimensionResult(
            name="Validity",
            weight=QUALITY_WEIGHTS.validity,
            score=100.0,
            issues=["No text columns to check for type mismatches."],
            numerator=0,
            denominator=0,
            severity="NONE",
            effect_on_overall=round(100.0 * QUALITY_WEIGHTS.validity / 100.0, 2),
            recommended_action="No action needed.",
            limitation="Cannot detect type mismatches without text columns.",
        )

    valid_columns = total_text_cols - invalid_columns
    score = round(valid_columns / total_text_cols * 100.0, 2)
    pct_invalid = round(invalid_columns / total_text_cols * 100.0, 2)

    issues = details if details else ["All text columns contain expected value types."]
    severity = _severity_from_pct(pct_invalid)
    action = (
        "No action needed."
        if severity == "NONE"
        else "Convert numeric-as-text and date-as-text columns in the Cleaning Studio."
    )
    limitation = (
        "Detection is based on a sample of up to 500 rows per column and may "
        "miss type mismatches in unsampled rows."
    )

    return DimensionResult(
        name="Validity",
        weight=QUALITY_WEIGHTS.validity,
        score=score,
        issues=issues,
        numerator=valid_columns,
        denominator=total_text_cols,
        severity=severity,
        effect_on_overall=round(score * QUALITY_WEIGHTS.validity / 100.0, 2),
        recommended_action=action,
        limitation=limitation,
    )


def _consistency_score(data: pd.DataFrame) -> DimensionResult:
    """Score consistency based on case and formatting inconsistencies in text columns."""

    n_rows, _ = data.shape
    text_columns = data.select_dtypes(include=["object", "string", "str"]).columns

    inconsistent_columns = 0
    details: list[str] = []
    for col in text_columns:
        series = data[col].dropna().astype(str)
        if series.empty:
            continue
        # Check for mixed case within the same normalized value
        normalized = series.str.strip().str.casefold()
        unique_normalized = normalized.nunique()
        unique_raw = series.nunique()
        # More raw forms than normalized forms indicates case/formatting inconsistency
        if unique_raw > unique_normalized and unique_normalized > 0:
            inconsistent_columns += 1
            excess = unique_raw - unique_normalized
            details.append(
                f"'{col}' has {excess} extra raw form(s) for {unique_normalized} normalized value(s) (case/formatting inconsistency)."
            )

    total_text_cols = len(text_columns)
    if total_text_cols == 0:
        return DimensionResult(
            name="Consistency",
            weight=QUALITY_WEIGHTS.consistency,
            score=100.0,
            issues=["No text columns to check for formatting consistency."],
            numerator=0,
            denominator=0,
            severity="NONE",
            effect_on_overall=round(100.0 * QUALITY_WEIGHTS.consistency / 100.0, 2),
            recommended_action="No action needed.",
            limitation="Cannot assess consistency without text columns.",
        )

    consistent_columns = total_text_cols - inconsistent_columns
    score = round(consistent_columns / total_text_cols * 100.0, 2)
    pct_inconsistent = round(inconsistent_columns / total_text_cols * 100.0, 2)

    issues = details if details else ["No case or formatting inconsistencies detected."]
    severity = _severity_from_pct(pct_inconsistent)
    action = (
        "No action needed."
        if severity == "NONE"
        else "Standardize category labels and text case in the Cleaning Studio."
    )
    limitation = (
        "Only detects case/formatting inconsistencies within text columns; "
        "cross-column or semantic inconsistencies are not measured."
    )

    return DimensionResult(
        name="Consistency",
        weight=QUALITY_WEIGHTS.consistency,
        score=score,
        issues=issues,
        numerator=consistent_columns,
        denominator=total_text_cols,
        severity=severity,
        effect_on_overall=round(score * QUALITY_WEIGHTS.consistency / 100.0, 2),
        recommended_action=action,
        limitation=limitation,
    )


def _uniqueness_score(data: pd.DataFrame) -> DimensionResult:
    """Score uniqueness based on duplicate-row percentage."""

    n_rows, _ = data.shape
    if n_rows == 0:
        return DimensionResult(
            name="Uniqueness",
            weight=QUALITY_WEIGHTS.uniqueness,
            score=None,
            issues=["Dataset has no rows; uniqueness cannot be assessed."],
            numerator=0,
            denominator=0,
            severity="INFO",
            effect_on_overall=0.0,
            recommended_action="Upload a dataset with data.",
            limitation="Cannot assess uniqueness of an empty dataset.",
        )

    n_duplicates = int(data.duplicated().sum())
    n_unique_rows = n_rows - n_duplicates
    score = round(n_unique_rows / n_rows * 100.0, 2)
    pct_duplicates = round(n_duplicates / n_rows * 100.0, 2)

    issues: list[str] = []
    if n_duplicates > 0:
        issues.append(f"{n_duplicates:,} of {n_rows:,} rows are exact duplicates ({pct_duplicates}%).")
    else:
        issues.append("No exact duplicate rows detected.")

    severity = _severity_from_pct(pct_duplicates)
    action = (
        "No action needed."
        if severity == "NONE"
        else "Review and remove exact duplicate rows in the Cleaning Studio."
    )
    limitation = (
        "Measures exact row duplicates only. Repeated values in a single "
        "column (e.g. many customers from the same city) are legitimate and "
        "not penalized."
    )

    return DimensionResult(
        name="Uniqueness",
        weight=QUALITY_WEIGHTS.uniqueness,
        score=score,
        issues=issues,
        numerator=n_unique_rows,
        denominator=n_rows,
        severity=severity,
        effect_on_overall=round(score * QUALITY_WEIGHTS.uniqueness / 100.0, 2),
        recommended_action=action,
        limitation=limitation,
    )


def _structural_score(data: pd.DataFrame) -> DimensionResult:
    """Score structural quality based on empty, constant, and duplicate-column problems."""

    n_rows, n_cols = data.shape

    empty_cols = 0
    constant_cols = 0
    duplicate_col_names = 0

    seen: set[str] = set()
    for col in data.columns:
        col_str = str(col)
        if col_str in seen:
            duplicate_col_names += 1
        seen.add(col_str)
        series = data[col]
        if series.isna().all():
            empty_cols += 1
        elif series.nunique(dropna=True) <= 1 and n_rows > 0:
            constant_cols += 1

    structural_issues = empty_cols + constant_cols + duplicate_col_names

    if n_cols == 0:
        return DimensionResult(
            name="Structural quality",
            weight=QUALITY_WEIGHTS.structural,
            score=None,
            issues=["Dataset has no columns; structural quality cannot be assessed."],
            numerator=0,
            denominator=0,
            severity="INFO",
            effect_on_overall=0.0,
            recommended_action="Upload a dataset with columns.",
            limitation="Cannot assess structural quality without columns.",
        )

    sound_columns = n_cols - structural_issues
    score = round(sound_columns / n_cols * 100.0, 2)
    pct_issues = round(structural_issues / n_cols * 100.0, 2)

    details: list[str] = []
    if empty_cols:
        details.append(f"{empty_cols} entirely empty column(s).")
    if constant_cols:
        details.append(f"{constant_cols} constant column(s).")
    if duplicate_col_names:
        details.append(f"{duplicate_col_names} duplicate column name(s).")
    if not details:
        details.append("No structural problems detected.")

    severity = _severity_from_pct(pct_issues)
    action = (
        "No action needed."
        if severity == "NONE"
        else "Drop empty/constant columns and rename duplicate headers in the Cleaning Studio."
    )
    limitation = (
        "Constant columns with a single meaningful value (e.g. a fixed "
        "treatment flag) are flagged even when intentional."
    )

    return DimensionResult(
        name="Structural quality",
        weight=QUALITY_WEIGHTS.structural,
        score=score,
        issues=details,
        numerator=sound_columns,
        denominator=n_cols,
        severity=severity,
        effect_on_overall=round(score * QUALITY_WEIGHTS.structural / 100.0, 2),
        recommended_action=action,
        limitation=limitation,
    )


def compute_quality_score(data: pd.DataFrame) -> QualityScoreResult:
    """Compute the overall 0-100 quality score and per-dimension results.

    Uses a weighted average of applicable dimension scores.  Dimensions that
    cannot be assessed (e.g. completeness on an empty dataset) are excluded
    and their weights are redistributed proportionally among the remaining
    dimensions.

    The source DataFrame is never mutated.
    """
    n_rows, n_cols = data.shape

    dimensions: list[DimensionResult] = [
        _completeness_score(data),
        _validity_score(data),
        _consistency_score(data),
        _uniqueness_score(data),
        _structural_score(data),
    ]

    applicable = [d for d in dimensions if d.score is not None]
    excluded = [d.name for d in dimensions if d.score is None]

    total_applicable_weight = sum(d.weight for d in applicable)
    if total_applicable_weight == 0:
        overall_score = 0.0
    else:
        weighted_sum = sum(
            d.score * d.weight for d in applicable
        )
        overall_score = round(weighted_sum / total_applicable_weight, 2)

    overall_score = max(0.0, min(100.0, overall_score))
    overall_label = QUALITY_THRESHOLDS.label(overall_score)
    interpretation = SCORE_INTERPRETATIONS[overall_label]

    return QualityScoreResult(
        overall_score=overall_score,
        overall_label=overall_label,
        overall_interpretation=interpretation.description,
        overall_recommendation=interpretation.recommendation,
        dimensions=dimensions,
        excluded_dimensions=excluded,
        n_rows=n_rows,
        n_cols=n_cols,
        computed_from="DataFlow Analytics quality scoring engine (configurable weights)",
    )


def format_quality_report(result: QualityScoreResult) -> list[dict[str, object]]:
    """Return a flat list of dimension summaries suitable for display or export."""
    rows: list[dict[str, object]] = []
    for d in result.dimensions:
        rows.append({
            "dimension": d.name,
            "weight": d.weight,
            "score": d.score,
            "severity": d.severity,
            "numerator": d.numerator,
            "denominator": d.denominator,
            "effect_on_overall": d.effect_on_overall,
            "issues": "; ".join(d.issues),
            "recommended_action": d.recommended_action,
            "limitation": d.limitation,
        })
    return rows
