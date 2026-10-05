"""Insights page — generated insights and recommendations."""

import pandas as pd
import streamlit as st

from core.insights import build_dashboard_summary
from core.quality import analyze_quality
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Insights page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("💡 Insights")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">💡</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to generate actionable insights.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available to analyze.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = bundle.working_df if hasattr(bundle, "working_df") else bundle.original_df
    quality_result = bundle.quality_result or analyze_quality(df)
    summary = build_dashboard_summary(df, quality_result=quality_result)

    st.subheader("Executive Summary")
    st.write(
        f"Overall quality is {summary['quality_score']:.1f} and the dataset is currently rated "
        f"{summary['grade']}. The most important next actions are aimed at improving reliability before "
        "sharing results externally."
    )

    st.subheader("Key Insights")
    if summary["insights"]:
        for insight in summary["insights"]:
            st.markdown(f"- **{insight['source_metric']}**: {insight['text']}")
    else:
        st.info("No high-confidence insights were generated for the current dataset.")

    st.subheader("Recommended Actions")
    if summary["recommendations"]:
        for rec in summary["recommendations"]:
            st.markdown(f"- **{rec['severity']}**: {rec['text']}")
    else:
        st.success("No action is required at the moment; continue monitoring the dataset.")

    st.markdown("</div>", unsafe_allow_html=True)
