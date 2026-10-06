"""Anomalies page — anomaly detection with multiple methods."""

import pandas as pd
import streamlit as st

from core.anomaly import detect_anomalies
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Anomalies page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🔍 Anomaly Detection")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to detect potential anomalies.
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
        st.info("Insufficient data for anomaly detection because no rows are available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if not numeric_cols:
        st.info("Insufficient data for anomaly detection because no numeric columns are available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    method = st.selectbox(
        "Detection method",
        ["iqr", "z", "modified_z", "rolling"],
        key="analysis_anomalies_method",
    )
    column = st.selectbox(
        "Column",
        numeric_cols + ["All numeric columns"],
        key="analysis_anomalies_column",
    )
    selected_column = None if column == "All numeric columns" else column

    anomalies = detect_anomalies(df, method=method, column=selected_column)
    if not anomalies:
        st.success("No potential anomalies were detected using the selected method.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    anomaly_df = pd.DataFrame(anomalies)
    anomaly_df = anomaly_df.sort_values(["score"], ascending=False)
    st.subheader("Potential anomalies detected")
    st.dataframe(anomaly_df[["column", "value", "score", "direction", "method"]], width="stretch")

    st.caption("Potential anomaly detected.")
    st.markdown("</div>", unsafe_allow_html=True)
