"""KPIs page — KPI detection and calculation."""

import streamlit as st

from core.kpi import detect_kpis
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the KPIs page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🎯 Key Performance Indicators")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🎯</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to automatically detect and calculate KPIs.
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
        st.info("Insufficient data for KPI calculation because no rows are available.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    metrics = detect_kpis(df)
    if not metrics:
        st.info("Insufficient data for KPI calculation because no matching KPI columns were found.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    cols = st.columns(min(3, len(metrics)))
    for idx, metric in enumerate(metrics):
        with cols[idx % len(cols)]:
            value = metric["value"]
            label = metric["name"]
            if metric.get("unit") == "percent":
                st.metric(label, f"{value:.2f}%")
            else:
                st.metric(label, f"{value:,.2f}")

    st.subheader("Detected KPI detail")
    st.dataframe(metrics, width="stretch")

    st.markdown("</div>", unsafe_allow_html=True)
