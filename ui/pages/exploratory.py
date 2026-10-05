"""Exploratory Analysis page — per-column explorer and recommended charts."""

import pandas as pd
import streamlit as st

from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Exploratory Analysis page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📈 Exploratory Analysis")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📈</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to explore visualizations and charts.
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
        st.info("No data available for exploratory analysis.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if df.shape[1] == 0:
        st.info("The current dataset has no columns to analyze.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    selected_col = st.selectbox("Column to explore", df.columns.tolist())
    ser = df[selected_col]

    st.subheader(f"Column: {selected_col}")
    if pd.api.types.is_numeric_dtype(ser):
        st.bar_chart(ser.value_counts().head(20))
    else:
        st.bar_chart(ser.value_counts().head(20))

    st.dataframe(ser.value_counts().head(20).reset_index().rename(columns={"index": "value", selected_col: "count"}), use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
