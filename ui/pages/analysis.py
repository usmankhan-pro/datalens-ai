"""Analysis page composing the existing analysis tools into tabs."""

import streamlit as st


def page() -> None:
    from ui.pages import anomalies, correlations, exploratory, kpis, statistics

    pages = [
        ("Exploratory", exploratory),
        ("Statistics", statistics),
        ("Correlations", correlations),
        ("Anomalies", anomalies),
        ("KPIs", kpis),
    ]
    tabs = st.tabs([title for title, _ in pages])
    for tab, (_, module) in zip(tabs, pages):
        with tab:
            module.page()