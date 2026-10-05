"""Central registry for Streamlit page objects and navigation groups."""

from __future__ import annotations

import streamlit as st


def _page(module, title: str, url_path: str, icon: str, default: bool = False):
    """Create a Streamlit page object for the app registry."""
    return st.Page(module.page, title=title, url_path=url_path, icon=icon, default=default)


def get_page_registry():
    """Return the canonical registry of page objects used throughout the app."""
    from ui.pages import (
        anomalies,
        cleaning,
        correlations,
        dashboard,
        exploratory,
        explorer,
        insights,
        kpis,
        profile,
        quality,
        reports,
        settings,
        statistics,
        upload,
    )

    return {
        "dashboard": _page(dashboard, "Dashboard", "dashboard", "📊", default=True),
        "upload": _page(upload, "Data Upload", "upload", "📤"),
        "profile": _page(profile, "Data Profile", "profile", "🔬"),
        "quality": _page(quality, "Data Quality", "quality", "✅"),
        "cleaning": _page(cleaning, "Data Cleaning", "cleaning", "🧹"),
        "exploratory": _page(exploratory, "Exploratory Analysis", "exploratory", "📈"),
        "statistics": _page(statistics, "Statistics", "statistics", "📐"),
        "anomalies": _page(anomalies, "Anomalies", "anomalies", "🔍"),
        "correlations": _page(correlations, "Correlations", "correlations", "🔗"),
        "kpis": _page(kpis, "KPIs", "kpis", "🎯"),
        "insights": _page(insights, "Insights", "insights", "💡"),
        "explorer": _page(explorer, "Data Explorer", "explorer", "🗂️"),
        "reports": _page(reports, "Reports", "reports", "📄"),
        "settings": _page(settings, "Settings", "settings", "⚙️"),
    }


def get_navigation():
    """Return the grouped sidebar navigation structure."""
    page_registry = get_page_registry()
    return {
        "Overview": [page_registry["dashboard"]],
        "Data": [
            page_registry["upload"],
            page_registry["profile"],
            page_registry["quality"],
            page_registry["cleaning"],
        ],
        "Analysis": [
            page_registry["exploratory"],
            page_registry["statistics"],
            page_registry["anomalies"],
            page_registry["correlations"],
        ],
        "Intelligence": [
            page_registry["kpis"],
            page_registry["insights"],
        ],
        "Tools": [
            page_registry["explorer"],
            page_registry["reports"],
            page_registry["settings"],
        ],
    }


def get_page_files():
    """Return the concrete source file paths for each registered page."""
    from ui.pages import (
        anomalies,
        cleaning,
        correlations,
        dashboard,
        exploratory,
        explorer,
        insights,
        kpis,
        profile,
        quality,
        reports,
        settings,
        statistics,
        upload,
    )

    return {
        "dashboard": dashboard.__file__,
        "upload": upload.__file__,
        "profile": profile.__file__,
        "quality": quality.__file__,
        "cleaning": cleaning.__file__,
        "exploratory": exploratory.__file__,
        "statistics": statistics.__file__,
        "anomalies": anomalies.__file__,
        "correlations": correlations.__file__,
        "kpis": kpis.__file__,
        "insights": insights.__file__,
        "explorer": explorer.__file__,
        "reports": reports.__file__,
        "settings": settings.__file__,
    }
