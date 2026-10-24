"""DataLens AI EDA package."""

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

__all__ = [
    "compute_eda_overview",
    "compute_univariate_analysis",
    "compute_missing_patterns",
    "compute_outlier_analysis",
    "compute_bivariate_analysis",
    "compute_target_analysis",
    "compute_time_trends",
    "compute_top_insights",
    "run_full_eda",
]
