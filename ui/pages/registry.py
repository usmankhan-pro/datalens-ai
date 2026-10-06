"""Central registry for the six top-level Streamlit pages."""

from __future__ import annotations

import streamlit as st


def _page(module, title: str, url_path: str, icon: str, default: bool = False):
    """Create a Streamlit page object for the app registry."""
    return st.Page(module.page, title=title, url_path=url_path, icon=icon, default=default)


@st.cache_resource
def get_page_registry():
    """Return the canonical registry of page objects used throughout the app."""
    from ui.pages import analysis, cleaning, data_quality, home, overview, report

    return {
        "home": _page(home, "Home", "home", "🏠", default=True),
        "overview": _page(overview, "Overview", "overview", "📊"),
        "data_quality": _page(data_quality, "Data Quality", "data-quality", "✅"),
        "clean": _page(cleaning, "Clean", "clean", "🧹"),
        "analysis": _page(analysis, "Analysis", "analysis", "📈"),
        "report": _page(report, "Report", "report", "📄"),
    }


def get_navigation():
    """Return the flat six-page navigation list."""
    return list(get_page_registry().values())


def get_page_files():
    """Return the concrete source file paths for each registered page."""
    from ui.pages import analysis, cleaning, data_quality, home, overview, report

    return {
        "home": home.__file__,
        "overview": overview.__file__,
        "data_quality": data_quality.__file__,
        "clean": cleaning.__file__,
        "analysis": analysis.__file__,
        "report": report.__file__,
    }
