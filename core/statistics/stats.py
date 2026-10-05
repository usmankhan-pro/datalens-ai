"""Statistics and correlation helpers for DataLens AI."""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd


def describe_numeric(series: pd.Series) -> Dict[str, Any]:
    """Return descriptive statistics for a numeric series with a plain-English interpretation."""
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return {
            "mean": None,
            "median": None,
            "std": None,
            "interpretation": "Insufficient data for descriptive statistics.",
        }

    mean = float(series.mean())
    median = float(series.median())
    std = float(series.std(ddof=1)) if len(series) > 1 else 0.0
    q1 = float(series.quantile(0.25))
    q3 = float(series.quantile(0.75))
    iqr = q3 - q1
    skew = float(series.skew())
    kurt = float(series.kurt())

    if abs(skew) > 1:
        skew_text = "strongly skewed"
    elif abs(skew) > 0.5:
        skew_text = "moderately skewed"
    else:
        skew_text = "fairly balanced"

    interpretation = (
        f"The distribution has a mean of {mean:.2f} and a median of {median:.2f}, "
        f"with a standard deviation of {std:.2f}. It is {skew_text} and its interquartile range is {iqr:.2f}."
    )

    return {
        "mean": mean,
        "median": median,
        "std": std,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "skewness": skew,
        "kurtosis": kurt,
        "interpretation": interpretation,
    }


def correlation_matrix(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """Compute Pearson and Spearman correlations for numeric columns."""
    numeric_df = df.select_dtypes(include=[np.number]).copy()
    if numeric_df.shape[1] < 2:
        return {"pearson": pd.DataFrame(), "spearman": pd.DataFrame()}

    pearson = numeric_df.corr(method="pearson")
    spearman = numeric_df.corr(method="spearman")
    return {"pearson": pearson, "spearman": spearman}


def infer_group_comparison(df: pd.DataFrame, group_col: str, value_col: str) -> Dict[str, Any]:
    """Run a simple group comparison using Welch t-test or Mann-Whitney U."""
    if group_col not in df.columns or value_col not in df.columns:
        raise KeyError("Group column or value column not found.")

    groups = df[group_col].dropna().unique()
    if len(groups) != 2:
        return {"test_name": "Not enough groups", "p_value": np.nan, "plain_english": "This comparison requires exactly two groups."}

    group_a = df.loc[df[group_col] == groups[0], value_col].dropna()
    group_b = df.loc[df[group_col] == groups[1], value_col].dropna()
    if len(group_a) < 2 or len(group_b) < 2:
        return {"test_name": "Insufficient data", "p_value": np.nan, "plain_english": "Each group needs enough observations to compare values reliably."}

    if len(group_a) >= 30 and len(group_b) >= 30:
        # Welch t-test is appropriate when each group is sufficiently large.
        from scipy import stats

        stat, p_value = stats.ttest_ind(group_a, group_b, equal_var=False)
        test_name = "Welch t-test"
    else:
        from scipy import stats

        stat, p_value = stats.mannwhitneyu(group_a, group_b)
        test_name = "Mann-Whitney U"

    interpretation = (
        f"The comparison between {groups[0]} and {groups[1]} uses {test_name}. "
        f"The p-value is {p_value:.4f}, which indicates whether the observed difference is likely to be meaningful."
    )

    return {
        "test_name": test_name,
        "statistic": float(stat),
        "p_value": float(p_value),
        "plain_english": interpretation,
    }


__all__ = ["describe_numeric", "correlation_matrix", "infer_group_comparison"]
