"""Correlations page — Pearson & Spearman correlation analysis."""

import pandas as pd
import streamlit as st

from core.statistics import correlation_matrix
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Correlations page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🔗 Correlations")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🔗</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to explore correlations between variables.
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
        st.info("No data available for correlation analysis.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    numeric_df = df.select_dtypes(include=['number'])
    if numeric_df.shape[1] < 2:
        st.info("At least two numeric columns are required for correlation analysis.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    corr = correlation_matrix(df)
    pearson = corr["pearson"]
    spearman = corr["spearman"]

    st.caption("⚠️ Correlation does not imply causation.")
    st.subheader("Pearson Correlation")
    st.dataframe(pearson, width="stretch")
    st.subheader("Spearman Correlation")
    st.dataframe(spearman, width="stretch")

    st.markdown("</div>", unsafe_allow_html=True)
