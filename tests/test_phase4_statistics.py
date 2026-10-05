import numpy as np
import pandas as pd

from core.statistics import describe_numeric, correlation_matrix, infer_group_comparison


def test_describe_numeric_returns_expected_stats():
    series = pd.Series([1, 2, 3, 4, 5])
    result = describe_numeric(series)

    assert result["mean"] == 3.0
    assert result["median"] == 3.0
    assert result["std"] > 0
    assert "interpretation" in result


def test_correlation_matrix_computes_pearson_and_spearman():
    df = pd.DataFrame({
        "x": [1, 2, 3, 4, 5],
        "y": [2, 4, 6, 8, 10],
    })
    result = correlation_matrix(df)

    assert "pearson" in result
    assert "spearman" in result
    assert abs(result["pearson"].loc["x", "y"] - 1.0) < 1e-6
    assert abs(result["spearman"].loc["x", "y"] - 1.0) < 1e-6


def test_group_comparison_handles_binary_categories():
    df = pd.DataFrame({
        "group": ["A", "A", "A", "B", "B", "B"],
        "value": [1, 2, 3, 4, 5, 6],
    })
    result = infer_group_comparison(df, "group", "value")

    assert result["test_name"] in {"Welch t-test", "Mann-Whitney U"}
    assert result["p_value"] >= 0
    assert "plain_english" in result
