"""Unit tests for Stage 3: Goal-Aware EDA Engine."""

import numpy as np
import pandas as pd
import pytest

from core.eda.engine import (
    compute_bivariate_analysis,
    compute_eda_overview,
    compute_missing_patterns,
    compute_outlier_analysis,
    compute_target_analysis,
    compute_time_trends,
    compute_top_insights,
    compute_univariate_analysis,
    run_full_eda,
)


@pytest.fixture
def sample_eda_dataset():
    """Create a DataFrame suitable for testing all EDA capabilities."""
    np.random.seed(42)
    n = 30
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    categories = ["Alpha"] * 18 + ["Beta"] * 10 + ["Gamma"] * 2  # Gamma has < 5 obs
    x1 = np.linspace(10, 100, n)
    x2 = x1 * 2 + np.random.normal(0, 5, n)
    x2[-1] = 500.0  # outlier
    target_class = ["Yes"] * 24 + ["No"] * 6  # 4:1 imbalance
    missing_col = [np.nan if i % 5 == 0 else 1.0 for i in range(n)]

    return pd.DataFrame({
        "timestamp": dates,
        "segment": categories,
        "feature_x1": x1,
        "feature_x2": x2,
        "target": target_class,
        "partially_missing": missing_col,
    })


def test_compute_eda_overview(sample_eda_dataset):
    ov = compute_eda_overview(sample_eda_dataset)
    assert ov["rows"] == 30
    assert ov["cols"] == 6
    assert ov["col_types"]["numeric"] == 3
    assert ov["col_types"]["categorical"] == 2
    assert ov["col_types"]["datetime"] == 1
    assert ov["missing_cells"] == 6
    assert ov["memory_mb"] > 0


def test_compute_univariate_analysis(sample_eda_dataset):
    uni = compute_univariate_analysis(sample_eda_dataset)
    num_stats = uni["numeric"]
    cat_stats = uni["categorical"]

    assert "feature_x1" in num_stats
    x1_stats = num_stats["feature_x1"]
    assert x1_stats["count"] == 30
    assert x1_stats["min"] == 10.0
    assert x1_stats["max"] == 100.0
    assert "skewness" in x1_stats
    assert len(x1_stats["hist_counts"]) > 0

    assert "segment" in cat_stats
    seg_stats = cat_stats["segment"]
    assert seg_stats["unique"] == 3
    assert seg_stats["mode"] == "Alpha"
    assert seg_stats["top_freq"] == 18


def test_compute_missing_patterns(sample_eda_dataset):
    miss = compute_missing_patterns(sample_eda_dataset)
    assert "partially_missing" in miss["column_missing"]
    assert miss["column_missing"]["partially_missing"]["count"] == 6
    assert "0 missing" in miss["row_missing_distribution"]


def test_compute_outlier_analysis(sample_eda_dataset):
    outliers = compute_outlier_analysis(sample_eda_dataset, factor=1.5)
    assert "feature_x2" in outliers
    x2_outlier = outliers["feature_x2"]
    assert x2_outlier["iqr_count"] >= 1
    assert x2_outlier["max_outlier"] == 500.0


def test_compute_bivariate_analysis_min_group_size(sample_eda_dataset):
    biv = compute_bivariate_analysis(sample_eda_dataset, min_group_size=5)
    pearson = biv["pearson"]
    assert "feature_x1" in pearson
    assert "feature_x2" in pearson["feature_x1"]

    # Verify group comparisons: Gamma has only 2 rows, so only Alpha (18) and Beta (10) qualify
    grp_comps = biv["group_comparisons"]
    for comp in grp_comps:
        if comp["categorical_col"] == "segment":
            assert comp["groups_compared"] == 2  # Alpha & Beta only, Gamma excluded!
            groups = [g["segment"] for g in comp["group_stats"]]
            assert "Alpha" in groups
            assert "Beta" in groups
            assert "Gamma" not in groups


def test_compute_target_analysis_categorical(sample_eda_dataset):
    target_data = compute_target_analysis(sample_eda_dataset, target_col="target")
    assert target_data["target_type"] == "categorical (classification)"
    assert target_data["imbalance_ratio"] == 4.0
    assert target_data["is_imbalanced"] is True


def test_compute_target_analysis_continuous(sample_eda_dataset):
    target_data = compute_target_analysis(sample_eda_dataset, target_col="feature_x1")
    assert "continuous (regression)" in target_data["target_type"]
    assert len(target_data["correlations"]) > 0


def test_compute_time_trends(sample_eda_dataset):
    trends = compute_time_trends(sample_eda_dataset)
    assert trends["date_column"] == "timestamp"
    assert trends["span_days"] == 29
    assert len(trends["period_counts"]) > 0


def test_compute_top_insights(sample_eda_dataset):
    insights = compute_top_insights(sample_eda_dataset, target_col="target")
    assert len(insights) == 5
    for ins in insights:
        assert "category" in ins
        assert "text" in ins
        assert len(ins["text"]) > 10


def test_run_full_eda(sample_eda_dataset):
    full = run_full_eda(sample_eda_dataset, target_col="target")
    assert "overview" in full
    assert "univariate" in full
    assert "bivariate" in full
    assert "target" in full
    assert "top_insights" in full
