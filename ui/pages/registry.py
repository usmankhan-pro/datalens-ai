"""Central registry for the goal-aware end-to-end Streamlit workflow pages."""

from __future__ import annotations

import streamlit as st


def _page(module, title: str, url_path: str, icon: str, default: bool = False):
    """Create a Streamlit page object for the app registry."""
    return st.Page(module.page, title=title, url_path=url_path, icon=icon, default=default)


@st.cache_resource
def get_page_registry():
    """Return the canonical registry of page objects used throughout the app."""
    from ui.pages import (
        analysis,
        cleaning,
        context,
        data_quality,
        eda,
        home,
        overview,
        plan,
        report,
        verdict,
    )

    return {
        "home": _page(home, "Upload Data", "home", "🏠", default=True),
        "context": _page(context, "Context Intake", "context", "🎯"),
        "overview": _page(overview, "Raw Profile", "overview", "📊"),
        "data_quality": _page(data_quality, "Quality Review", "data-quality", "✅"),
        "plan": _page(plan, "Action Plan", "plan", "📋"),
        "clean": _page(cleaning, "Cleaning Pipeline", "clean", "🧹"),
        "eda": _page(eda, "EDA Deep Dive", "eda", "📈"),
        "analysis": _page(analysis, "Analytics Tools", "analysis", "🔬"),
        "verdict": _page(verdict, "Readiness Verdict", "verdict", "⚖️"),
        "report": _page(report, "Export & Reports", "report", "📦"),
    }


def get_navigation():
    """Return the ordered workflow navigation list."""
    return list(get_page_registry().values())


def get_page_files():
    """Return the concrete source file paths for each registered page."""
    from ui.pages import (
        analysis,
        cleaning,
        context,
        data_quality,
        eda,
        home,
        overview,
        plan,
        report,
        verdict,
    )

    return {
        "home": home.__file__,
        "context": context.__file__,
        "overview": overview.__file__,
        "data_quality": data_quality.__file__,
        "plan": plan.__file__,
        "clean": cleaning.__file__,
        "eda": eda.__file__,
        "analysis": analysis.__file__,
        "verdict": verdict.__file__,
        "report": report.__file__,
    }
