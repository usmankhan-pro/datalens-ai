"""Analysis page composing the EDA engine and analytical tools into tabs."""

import streamlit as st


def page() -> None:
    from ui.pages import eda, anomalies, correlations, exploratory, kpis, statistics

    pages = [
        ("EDA Deep Dive", eda),
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