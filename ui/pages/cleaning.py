"""
Data Cleaning page — cleaning operations workspace.
Implementation coming in Phase 3.
"""

import streamlit as st


def page() -> None:
    """Render the Data Cleaning page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🧹 Data Cleaning")
    st.markdown("---")

    from core.utils.state import has_dataset

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🧹</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to access the cleaning workspace.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("🚧 Data Cleaning — Coming in Phase 3")

    st.markdown("</div>", unsafe_allow_html=True)
