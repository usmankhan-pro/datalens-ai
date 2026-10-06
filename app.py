"""
Automated Data Quality & Analytics Platform

Main application entrypoint for the platform. It configures Streamlit
page settings, injects the theme CSS, builds the sidebar navigation,
and provides a dark/light mode toggle for the analytics workflow.
"""

import html
import streamlit as st

# --- Page Config (must be first Streamlit call) ---
st.set_page_config(
    page_title="Automated Data Quality & Analytics Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Theme CSS Injection ---
from core.utils.state import get_theme, toggle_theme, has_dataset, get_bundle
from ui.theme.css import inject_css

inject_css(get_theme())

from ui.pages.registry import get_navigation

# --- Navigation ---
pg = st.navigation(get_navigation())

# --- Sidebar ---
with st.sidebar:
    # App branding
    st.markdown(
        """
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <div style="font-size: 1.8rem; margin-bottom: 0.25rem;">�</div>
            <div style="font-size: 1.1rem; font-weight: 700; letter-spacing: -0.02em; line-height: 1.4;">
                Automated Data Quality<br>& Analytics Platform
            </div>
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.15rem;">
                DataLens AI
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Dataset status indicator
    if has_dataset():
        bundle = get_bundle()
        st.markdown(
            f"""
            <div class="datalens-card" style="padding: 0.75rem; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="color: var(--success); font-size: 1.1rem;">●</span>
                    <div>
                        <div style="font-weight: 600; font-size: 0.85rem;">
                            {html.escape(bundle.file_meta.name if bundle else 'Dataset')}
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">
                            {f'{bundle.file_meta.rows:,} rows × {bundle.file_meta.cols} cols' if bundle else ''}
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div class="datalens-card" style="padding: 0.75rem; margin-bottom: 1rem; opacity: 0.6;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="color: var(--text-muted); font-size: 1.1rem;">○</span>
                    <div>
                        <div style="font-weight: 500; font-size: 0.85rem; color: var(--text-muted);">
                            No dataset loaded
                        </div>
                        <div style="font-size: 0.75rem; color: var(--text-muted);">
                            Upload or try the demo
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    with st.expander("Settings", expanded=False):
        current_theme = get_theme()
        theme_icon = "🌙" if current_theme == "dark" else "☀️"
        theme_label = "Dark Mode" if current_theme == "dark" else "Light Mode"
        if st.button(f"{theme_icon} {theme_label}", key="sidebar_theme_toggle"):
            toggle_theme()
            st.rerun()
        st.caption("All data is processed in memory for this session.")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; padding: 0.5rem 0;">
            <div style="font-size: 0.7rem; color: var(--text-muted);">
                DataLens AI v0.1.0
            </div>
            <div style="font-size: 0.65rem; color: var(--text-muted); margin-top: 0.25rem;">
                🔒 All data processed in memory
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- Run Selected Page ---
pg.run()
