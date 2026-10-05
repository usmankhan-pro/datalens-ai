"""
Settings page — theme, privacy, session configuration.
Implementation coming in Phase 8.
"""

import streamlit as st


def page() -> None:
    """Render the Settings page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("⚙️ Settings")
    st.markdown("---")

    st.info("🚧 Settings — Coming in Phase 8")

    # Privacy notice placeholder
    st.markdown(
        """
        <div class="privacy-notice">
            🔒 <strong>Privacy:</strong> All data is processed in memory. 
            No uploads are stored on disk. Session data is isolated.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)
