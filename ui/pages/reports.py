"""
Reports page — PDF, Excel, CSV report generation.
Implementation coming in Phase 7.
"""

import streamlit as st


def page() -> None:
    """Render the Reports page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📄 Reports")
    st.markdown("---")

    from core.utils.state import has_dataset

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📄</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to generate PDF, Excel, and CSV reports.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("🚧 Reports — Coming in Phase 7")

    st.markdown("</div>", unsafe_allow_html=True)
