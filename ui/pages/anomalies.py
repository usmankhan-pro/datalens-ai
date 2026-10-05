"""
Anomalies page — anomaly detection with multiple methods.
Implementation coming in Phase 5.
"""

import streamlit as st


def page() -> None:
    """Render the Anomalies page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🔍 Anomaly Detection")
    st.markdown("---")

    from core.utils.state import has_dataset

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
    else:
        st.info("🚧 Anomaly Detection — Coming in Phase 5")

    st.markdown("</div>", unsafe_allow_html=True)
