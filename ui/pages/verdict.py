"""Readiness Verdict UI page for DataLens AI."""

import streamlit as st
from core.utils.state import get_bundle, has_dataset, set_bundle
from core.verdict import ReadinessVerdict, evaluate_readiness


def page() -> None:
    """Render the Readiness Verdict page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("⚖️ Goal Readiness Verdict")
    st.caption("Objective pass/warn/fail evaluation verifying whether your dataset is prepared for your stated goal.")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">⚖️</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload and clean a dataset to generate a goal readiness verdict.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        return

    df = bundle.working_df
    ctx = getattr(bundle, "user_context", None)

    # Evaluate readiness
    verdict: ReadinessVerdict = evaluate_readiness(df, context=ctx)
    bundle.readiness_verdict = verdict
    set_bundle(bundle)

    # 1. Overall Status Banner
    if verdict.overall_status == "PASS":
        status_bg = "#dcfce7"
        status_color = "#15803d"
        status_text = "READY (PASS)"
        status_desc = "The dataset satisfies all critical criteria for your stated goal."
    elif verdict.overall_status == "WARN":
        status_bg = "#fef3c7"
        status_color = "#b45309"
        status_text = "QUALIFIED (WARN)"
        status_desc = "Dataset is usable, but potential issues were detected that warrant attention."
    else:
        status_bg = "#fee2e2"
        status_color = "#b91c1c"
        status_text = "NOT READY (FAIL)"
        status_desc = "Critical blockers detected. Remediation in the cleaning pipeline is recommended before downstream use."

    st.markdown(
        f"""
        <div class="datalens-card" style="padding: 1.25rem; border-left: 6px solid {status_color}; background-color: {status_bg}15; margin-bottom: 1.5rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.8rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">
                        Goal: {verdict.goal.upper()}
                    </div>
                    <div style="font-size: 1.5rem; font-weight: 800; color: {status_color}; margin-top: 0.2rem;">
                        {status_text}
                    </div>
                    <div style="font-size: 0.9rem; margin-top: 0.25rem;">
                        {status_desc}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 2.2rem; font-weight: 900; color: {status_color};">
                        {verdict.readiness_score:.0f}
                        <span style="font-size: 1rem; color: var(--text-muted); font-weight: 500;">/ 100</span>
                    </div>
                    <div style="font-size: 0.75rem; color: var(--text-muted);">Readiness Score</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mini scorecard
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Checks", verdict.total_checks)
    c2.metric("Passed", verdict.passed_checks)
    c3.metric("Warnings", verdict.warn_checks)
    c4.metric("Failures", verdict.failed_checks)

    st.markdown("---")

    # 2. Checklist Items
    st.subheader("📋 Evaluation Criteria Checklist")

    for item in verdict.items:
        if item.status == "PASS":
            badge = '<span style="background-color: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">PASS</span>'
        elif item.status == "WARN":
            badge = '<span style="background-color: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">WARN</span>'
        else:
            badge = '<span style="background-color: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">FAIL</span>'

        with st.container():
            st.markdown(
                f"""
                <div class="datalens-card" style="padding: 0.85rem 1.15rem; margin-bottom: 0.5rem; border: 1px solid var(--border, #e2e8f0);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; font-size: 0.95rem;">{item.name}</span>
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="font-family: monospace; font-size: 0.85rem; color: var(--text-muted);">{item.metric_value}</span>
                            {badge}
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 0.35rem;">
                        {item.reason}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if item.remaining_action:
                st.caption(f"👉 **Suggested Action:** {item.remaining_action}")

    st.markdown("---")

    # 3. Decision Support Disclaimer
    st.info(f"⚖️ **Notice:** {verdict.disclaimer}")

    st.markdown("---")

    # Navigation actions
    n1, n2 = st.columns(2)
    with n1:
        if st.button("🧹 Remediate in Cleaning Workspace", key="verdict_goto_clean"):
            from ui.pages.registry import get_page_registry
            st.switch_page(get_page_registry()["clean"])
    with n2:
        if st.button("📦 Proceed to Export & Reports ➜", type="primary", key="verdict_goto_export"):
            from ui.pages.registry import get_page_registry
            st.switch_page(get_page_registry()["report"])

    st.markdown("</div>", unsafe_allow_html=True)
