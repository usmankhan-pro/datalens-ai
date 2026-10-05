"""
Insights page — generated insights and recommendations.
Implementation coming in Phase 6.
"""

import streamlit as st


def page() -> None:
    """Render the Insights page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("💡 Insights")
    st.markdown("---")

    from core.utils.state import has_dataset

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">💡</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to generate actionable insights.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("🚧 Insights — Coming in Phase 6")

    st.markdown("</div>", unsafe_allow_html=True)
