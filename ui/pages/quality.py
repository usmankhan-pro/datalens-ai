"""Data Quality page — quality score and issue review."""

import pandas as pd
import streamlit as st

from core.quality import analyze_quality
from core.utils.state import get_bundle, has_dataset, set_bundle


def page() -> None:
    """Render the Data Quality page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("✅ Data Quality")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to see quality scores and detected issues.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for quality scoring.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    quality_result = bundle.quality_result or analyze_quality(bundle.original_df)
    bundle.quality_result = quality_result
    set_bundle(bundle)

    score = quality_result["overall_score"]
    grade = quality_result["grade"]

    col1, col2, col3 = st.columns([1.5, 1.5, 3])
    with col1:
        st.metric("Overall Score", f"{score:.1f}")
    with col2:
        st.metric("Grade", grade)
    with col3:
        st.caption("Accuracy / Validity Indicator: this score is a risk indicator, not proof of real-world accuracy.")

    st.subheader("Dimension Scores")
    dim_df = pd.DataFrame(
        [
            {
                "Dimension": name,
                "Score": values["score"],
                "Explanation": values["explanation"],
            }
            for name, values in quality_result["dimensions"].items()
        ]
    )
    st.dataframe(dim_df, use_container_width=True, hide_index=True)

    st.subheader("Issues Detected")
    issues = quality_result["issues"]
    if issues:
        issues_df = pd.DataFrame(issues)
        st.dataframe(issues_df, use_container_width=True, hide_index=True)
    else:
        st.success("No quality issues were detected in the current dataset.")

    st.markdown("</div>", unsafe_allow_html=True)
