"""Overview page entry point."""

import streamlit as st


def page() -> None:
    from core.utils.state import has_dataset

    if not has_dataset():
        st.title("Overview")
        st.info("Upload a dataset first to see its overview.")
        if st.button("Go to Home", key="overview_home_button"):
            from ui.pages.registry import get_page_registry

            st.switch_page(get_page_registry()["home"])
        return

    from ui.pages.dashboard import page as render_dashboard

    render_dashboard()