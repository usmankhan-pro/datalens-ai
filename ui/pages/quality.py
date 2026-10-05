"""
Data Quality page — quality score and issues.
Implementation coming in Phase 2.
"""

import streamlit as st


def page() -> None:
    """Render the Data Quality page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("✅ Data Quality")
    st.markdown("---")

    from core.utils.state import has_dataset

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to see quality scores and detected issues.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("🚧 Data Quality — Coming in Phase 2")

    st.markdown("</div>", unsafe_allow_html=True)
