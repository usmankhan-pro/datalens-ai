"""Unit tests for Stage 5: Goal Readiness Verdict."""

import numpy as np
import pandas as pd
import pytest

from core.context.models import UserContext
from core.verdict.verdict import ReadinessVerdict, evaluate_readiness


def test_verdict_ml_unlabeled_target_fails():
    # DataFrame with missing target values
    df = pd.DataFrame({
        "feature1": [1.0, 2.0, 3.0, 4.0],
        "target": [1, 0, np.nan, 1],
    })
    ctx = UserContext(goal="ml", target_column="target")
    verdict = evaluate_readiness(df, context=ctx)

    assert isinstance(verdict, ReadinessVerdict)
    assert verdict.overall_status == "FAIL"

    target_check = next(item for item in verdict.items if item.name == "Target Label Completeness")
    assert target_check.status == "FAIL"
    assert "cannot train" in target_check.reason
    assert target_check.remaining_action is not None


def test_verdict_ml_duplicates_fail():
    # DataFrame with duplicate rows
    df = pd.DataFrame({
        "f1": [1, 2, 2, 4] * 10,
        "f2": [10, 20, 20, 40] * 10,
        "target": [1, 0, 0, 1] * 10,
    })
    ctx = UserContext(goal="ml", target_column="target")
    verdict = evaluate_readiness(df, context=ctx)

    dup_check = next(item for item in verdict.items if item.name == "Data Leakage & Duplication")
    assert dup_check.status == "FAIL"
    assert verdict.failed_checks >= 1


def test_verdict_reporting_pass():
    # Clean reporting dataset
    df = pd.DataFrame({
        "order_id": [1, 2, 3, 4, 5],
        "order_date": pd.date_range("2023-01-01", periods=5),
        "revenue": [100.0, 200.0, 300.0, 400.0, 500.0],
    })
    ctx = UserContext(goal="reporting")
    verdict = evaluate_readiness(df, context=ctx)

    assert verdict.overall_status == "PASS"
    assert verdict.readiness_score >= 90.0
    assert verdict.failed_checks == 0
    assert "Disclaimer" in verdict.disclaimer


def test_verdict_empty_dataframe_fails():
    empty_df = pd.DataFrame()
    verdict = evaluate_readiness(empty_df)
    assert verdict.overall_status == "FAIL"
    assert verdict.readiness_score == 0.0
