"""
Statistics page — descriptive stats, distribution, CI, group comparison.
Implementation coming in Phase 4.
"""

import streamlit as st


def page() -> None:
    """Render the Statistics page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📐 Statistics")
    st.markdown("---")

    from core.utils.state import has_dataset

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
    else:
        st.info("🚧 Statistics — Coming in Phase 4")

    st.markdown("</div>", unsafe_allow_html=True)
