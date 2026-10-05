"""
Correlations page — Pearson & Spearman correlation analysis.
Implementation coming in Phase 4.
"""

import streamlit as st


def page() -> None:
    """Render the Correlations page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🔗 Correlations")
    st.markdown("---")

    from core.utils.state import has_dataset

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🔗</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to explore correlations between variables.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("🚧 Correlations — Coming in Phase 4")
        st.caption("⚠️ Correlation does not imply causation.")

    st.markdown("</div>", unsafe_allow_html=True)
