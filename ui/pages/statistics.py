"""Statistics page — descriptive stats, distribution, CI, and group comparison."""

import pandas as pd
import streamlit as st

from core.statistics import describe_numeric, infer_group_comparison
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Statistics page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📐 Statistics")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📐</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to run statistical analysis.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    df = bundle.working_df if bundle is not None else None
    if df is None or df.empty:
        st.info("No data available for descriptive statistics.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if not numeric_cols:
        st.info("No numeric columns are available for statistical analysis.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    selected_col = st.selectbox("Numeric column", numeric_cols)
    series = df[selected_col]
    stats = describe_numeric(series)

    st.subheader(f"Descriptive Statistics: {selected_col}")
    stats_df = pd.DataFrame([
        {"Metric": "Mean", "Value": stats["mean"]},
        {"Metric": "Median", "Value": stats["median"]},
        {"Metric": "Std Dev", "Value": stats["std"]},
        {"Metric": "Q1", "Value": stats["q1"]},
        {"Metric": "Q3", "Value": stats["q3"]},
        {"Metric": "IQR", "Value": stats["iqr"]},
        {"Metric": "Skewness", "Value": stats["skewness"]},
        {"Metric": "Kurtosis", "Value": stats["kurtosis"]},
    ])
    st.dataframe(stats_df, use_container_width=True, hide_index=True)
    st.write(stats["interpretation"])

    categorical_cols = df.select_dtypes(exclude=['number']).columns.tolist()
    if categorical_cols and len(categorical_cols) >= 2:
        cat_col = st.selectbox("Group column", categorical_cols)
        if df[cat_col].nunique() == 2:
            other_col = st.selectbox("Numeric comparison column", numeric_cols)
            comparison = infer_group_comparison(df[[cat_col, other_col]].dropna(), cat_col, other_col)
            st.subheader("Group Comparison")
            st.write(comparison["test_name"])
            st.write(f"P-value: {comparison['p_value']:.4f}")
            st.write(comparison["plain_english"])

    st.markdown("</div>", unsafe_allow_html=True)
