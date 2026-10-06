"""Data quality page combining profile and quality review tabs."""

import streamlit as st


def page() -> None:
    from ui.pages import profile, quality

    profile_tab, quality_tab = st.tabs(["Profile", "Quality Score & Issues"])
    with profile_tab:
        profile.page()
    with quality_tab:
        quality.page()