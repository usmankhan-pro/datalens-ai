"""Validation rules and checks for dataset quality.

Pure, testable functions that inspect a DataFrame and return structured
validation results.  No UI dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ValidationResult:
    """Result of a single validation check."""

    check: str
    passed: bool
    column: str | None
    detail: str
    severity: str  # "HIGH", "MEDIUM", "LOW", "INFO"
    affected_count: int


@dataclass(frozen=True)
class ValidationReport:
    """Collection of validation results for a dataset."""

    results: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[ValidationResult]:
        return [r for r in self.results if not r.passed]

    @property
    def high_severity(self) -> list[ValidationResult]:
        return [r for r in self.results if r.severity == "HIGH"]

    def to_dict(self) -> list[dict[str, object]]:
        return [
            {
                "check": r.check,
                "passed": r.passed,
                "column": r.column,
                "detail": r.detail,
                "severity": r.severity,
                "affected_count": r.affected_count,
            }
            for r in self.results
        ]


def validate_no_empty_dataset(data: pd.DataFrame) -> ValidationResult:
    """Check that the dataset has at least one row and one column."""
    n_rows, n_cols = data.shape
    if n_rows == 0 or n_cols == 0:
        return ValidationResult(
            check="non_empty_dataset",
            passed=False,
            column=None,
            detail=f"Dataset has {n_rows} rows and {n_cols} columns.",
            severity="HIGH",
            affected_count=0,
        )
    return ValidationResult(
        check="non_empty_dataset",
        passed=True,
        column=None,
        detail=f"Dataset has {n_rows} rows and {n_cols} columns.",
        severity="INFO",
        affected_count=0,
    )


def validate_no_duplicate_columns(data: pd.DataFrame) -> ValidationResult:
    """Check that column names are unique."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for col in data.columns:
        col_str = str(col)
        if col_str in seen:
            duplicates.append(col_str)
        seen.add(col_str)

    if duplicates:
        return ValidationResult(
            check="unique_column_names",
            passed=False,
            column=", ".join(duplicates),
            detail=f"Duplicate column name(s): {', '.join(duplicates)}.",
            severity="HIGH",
            affected_count=len(duplicates),
        )
    return ValidationResult(
        check="unique_column_names",
        passed=True,
        column=None,
        detail="All column names are unique.",
        severity="INFO",
        affected_count=0,
    )


def validate_missing_values_below_threshold(
    data: pd.DataFrame, threshold_pct: float = 50.0
) -> list[ValidationResult]:
    """Check each column for missing values above a threshold."""
    results: list[ValidationResult] = []
    n_rows = len(data)
    if n_rows == 0:
        return results

    for col in data.columns:
        n_missing = int(data[col].isna().sum())
        pct = n_missing / n_rows * 100.0
        if pct > 0:
            severity = "HIGH" if pct >= threshold_pct else ("MEDIUM" if pct >= 20.0 else "LOW")
            results.append(
                ValidationResult(
                    check="missing_values",
                    passed=pct < threshold_pct,
                    column=str(col),
                    detail=f"{n_missing:,} of {n_rows:,} values missing ({pct:.1f}%).",
                    severity=severity,
                    affected_count=n_missing,
                )
            )
    return results


def validate_no_all_null_columns(data: pd.DataFrame) -> ValidationResult:
    """Check for columns that are entirely null."""
    all_null = [str(col) for col in data.columns if data[col].isna().all()]
    if all_null:
        return ValidationResult(
            check="no_all_null_columns",
            passed=False,
            column=", ".join(all_null),
            detail=f"Entirely empty column(s): {', '.join(all_null)}.",
            severity="HIGH",
            affected_count=len(all_null),
        )
    return ValidationResult(
        check="no_all_null_columns",
        passed=True,
        column=None,
        detail="No entirely empty columns.",
        severity="INFO",
        affected_count=0,
    )


def validate_no_constant_columns(data: pd.DataFrame) -> ValidationResult:
    """Check for columns with a single distinct value (excluding all-null)."""
    n_rows = len(data)
    constant = []
    for col in data.columns:
        series = data[col]
        if not series.isna().all() and series.nunique(dropna=True) <= 1:
            constant.append(str(col))

    if constant:
        return ValidationResult(
            check="no_constant_columns",
            passed=False,
            column=", ".join(constant),
            detail=f"Constant column(s): {', '.join(constant)}.",
            severity="LOW",
            affected_count=len(constant),
        )
    return ValidationResult(
        check="no_constant_columns",
        passed=True,
        column=None,
        detail="No constant columns.",
        severity="INFO",
        affected_count=0,
    )


def validate_duplicate_rows_below_threshold(
    data: pd.DataFrame, threshold_pct: float = 10.0
) -> ValidationResult:
    """Check that duplicate-row percentage is below a threshold."""
    n_rows = len(data)
    if n_rows == 0:
        return ValidationResult(
            check="duplicate_rows",
            passed=True,
            column=None,
            detail="No rows to check for duplicates.",
            severity="INFO",
            affected_count=0,
        )
    n_duplicates = int(data.duplicated().sum())
    pct = n_duplicates / n_rows * 100.0
    passed = pct < threshold_pct
    severity = "HIGH" if pct >= threshold_pct else ("MEDIUM" if pct >= 5.0 else "LOW")
    return ValidationResult(
        check="duplicate_rows",
        passed=passed,
        column=None,
        detail=f"{n_duplicates:,} duplicate row(s) ({pct:.1f}% of rows).",
        severity=severity,
        affected_count=n_duplicates,
    )


def run_all_validations(
    data: pd.DataFrame,
    missing_threshold_pct: float = 50.0,
    duplicate_threshold_pct: float = 10.0,
) -> ValidationReport:
    """Run every built-in validation and return a combined report."""
    results: list[ValidationResult] = []

    results.append(validate_no_empty_dataset(data))
    results.append(validate_no_duplicate_columns(data))
    results.append(validate_no_all_null_columns(data))
    results.append(validate_no_constant_columns(data))
    results.append(validate_duplicate_rows_below_threshold(data, duplicate_threshold_pct))
    results.extend(
        validate_missing_values_below_threshold(data, missing_threshold_pct)
    )

    return ValidationReport(results=results)
