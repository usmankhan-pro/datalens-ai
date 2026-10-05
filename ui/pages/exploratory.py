"""
Exploratory Analysis page — per-column explorer and recommended charts.
Implementation coming in Phase 4.
"""

import streamlit as st


def page() -> None:
    """Render the Exploratory Analysis page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📈 Exploratory Analysis")
    st.markdown("---")

    from core.utils.state import has_dataset

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
    else:
        st.info("🚧 Exploratory Analysis — Coming in Phase 4")

    st.markdown("</div>", unsafe_allow_html=True)
