"""Report page composing exports, data exploration, and insights."""

import streamlit as st


def page() -> None:
    from ui.pages import explorer, insights, reports

    pages = [
        ("Report & Export", reports),
        ("Data Explorer", explorer),
        ("Insights", insights),
    ]
    tabs = st.tabs([title for title, _ in pages])
    for tab, (_, module) in zip(tabs, pages):
        with tab:
            module.page()