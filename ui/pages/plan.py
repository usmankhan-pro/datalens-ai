"""Action Plan page — Goal-aware recommendations mapped from context and quality checks."""

from datetime import datetime
import streamlit as st

from core.cleaning import apply_operation
from core.planner import ActionPlan, create_action_plan
from core.utils.state import TransformRecord, get_bundle, has_dataset, set_bundle


def page() -> None:
    """Render the Action Plan page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📋 Goal-Aware Action Plan")
    st.caption("Ordered data preparation plan mapped from detected issues and your analytical intent.")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to generate a personalized action plan.
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

    # Generate or refresh plan
    plan: ActionPlan = create_action_plan(df, context=ctx)
    bundle.action_plan = plan
    set_bundle(bundle)

    # 1. Plan Overview Bar
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Analytical Goal", plan.goal.upper())
    with c2:
        st.metric("Detected Domain", plan.domain)
    with c3:
        st.metric("Current Quality Score", f"{plan.initial_quality_score:.1f}")
    with c4:
        st.metric(
            "Potential Cleaned Score",
            f"{plan.potential_quality_score:.1f}",
            delta=f"{plan.potential_quality_score - plan.initial_quality_score:+.1f}",
        )

    if plan.target_column:
        st.info(f"🎯 Target Variable Configured: **`{plan.target_column}`**")

    st.markdown("---")

    # 2. Batch Execution Controls
    safe_acts = plan.safe_actions()
    b1, b2 = st.columns([2, 1])

    with b1:
        if st.button(
            f"⚡ Apply All {len(safe_acts)} Safe Plan Steps Now",
            type="primary",
            disabled=len(safe_acts) == 0,
            key="plan_apply_all_safe_btn",
        ):
            bundle.push_snapshot()
            temp_df = bundle.working_df.copy()
            applied_records = []
            for act in safe_acts:
                res = apply_operation(temp_df, act.operation, act.params)
                temp_df = res["df"]
                applied_records.append(
                    TransformRecord(
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        operation=act.operation,
                        columns=act.columns,
                        params=act.params,
                        rows_affected=res["rows_affected"],
                        stage=act.stage,
                        risk="safe",
                    )
                )
            bundle.working_df = temp_df
            bundle.transformation_history.extend(applied_records)
            set_bundle(bundle)
            st.success(f"Applied {len(safe_acts)} safe transformations successfully!")
            st.rerun()

    with b2:
        if st.button("🧹 Open Cleaning Workspace", key="plan_go_to_cleaning"):
            from ui.pages.registry import get_page_registry
            st.switch_page(get_page_registry()["clean"])

    st.markdown("---")

    # 3. Action Plan Steps
    st.subheader(f"Recommended Cleaning Sequence ({len(plan.actions)} steps)")

    if not plan.actions:
        st.success("🎉 No issues detected! Your dataset is clean and matches your goal specifications.")
    else:
        for act in plan.actions:
            # Color-coded risk badge
            if act.risk == "safe":
                risk_badge = '<span style="background-color: #dcfce7; color: #15803d; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">SAFE</span>'
            elif act.risk == "review":
                risk_badge = '<span style="background-color: #fef3c7; color: #b45309; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">REVIEW</span>'
            else:
                risk_badge = '<span style="background-color: #fee2e2; color: #b91c1c; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">RISKY (APPROVAL REQUIRED)</span>'

            # Severity badge
            sev_color = "#ef4444" if act.severity == "CRITICAL" else ("#f97316" if act.severity == "HIGH" else "#64748b")
            sev_badge = f'<span style="color: {sev_color}; font-size: 0.75rem; font-weight: 700; margin-left: 0.5rem;">{act.severity}</span>'

            # Score impact
            delta_str = f"+{act.score_impact:.1f} pts" if act.score_impact > 0 else f"{act.score_impact:.1f} pts"
            impact_badge = f'<span style="font-weight: 600; color: #2563eb; font-size: 0.8rem;">Score Impact: {delta_str}</span>'

            st.markdown(
                f"""
                <div class="datalens-card" style="padding: 1rem; margin-bottom: 0.75rem; border: 1px solid var(--border, #e2e8f0);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="font-weight: 700; font-size: 0.95rem;">Step {act.step_number}: {act.title}</span>
                            {sev_badge}
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.75rem;">
                            {impact_badge}
                            {risk_badge}
                        </div>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-muted, #64748b); margin-top: 0.25rem;">
                        <b>Why:</b> {act.reason}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
