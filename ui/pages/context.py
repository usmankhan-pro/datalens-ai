"""Context Intake page — goal, audience, target column, and domain confirmation."""

import streamlit as st
from core.context import UserContext, detect_domain
from core.utils.state import get_bundle, has_dataset, set_bundle


def page() -> None:
    """Render the Context Intake page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🎯 Analytical Context Intake")
    st.caption("Tell DataLens AI how this dataset will be utilized to generate a goal-aware action plan.")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🎯</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset first to set analytical context and detect domain.
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

    # Auto-detect domain from columns
    detected_domain, confidence = detect_domain(list(df.columns))

    existing_ctx: UserContext = getattr(bundle, "user_context", None) or UserContext(
        domain=detected_domain,
        domain_confidence=confidence,
    )

    st.subheader("1. Analytical Intent")

    goal_options = {
        "reporting": "📊 Executive / Operational Reporting (Prioritize KPIs, dates, deduplication)",
        "ml": "🤖 Machine Learning (Prioritize leakages, cardinality, imputations, balance)",
        "business_analysis": "📈 Business Analysis (Prioritize distributions, correlations, outliers)",
        "research": "🔬 Scientific / Academic Research (Prioritize data integrity, hypothesis testing)",
        "other": "📋 General Data Preparation",
    }

    current_goal_key = existing_ctx.goal if existing_ctx.goal in goal_options else "business_analysis"
    selected_goal = st.radio(
        "Why is this data uploaded?",
        options=list(goal_options.keys()),
        format_func=lambda k: goal_options[k],
        index=list(goal_options.keys()).index(current_goal_key),
        key="context_goal_radio",
    )

    st.markdown("---")
    st.subheader("2. Target Column & Audience")

    col1, col2 = st.columns(2)

    with col1:
        target_options = ["(None / Unsupervised)"] + list(df.columns)
        default_target_idx = 0
        if existing_ctx.target_column and existing_ctx.target_column in target_options:
            default_target_idx = target_options.index(existing_ctx.target_column)

        chosen_target = st.selectbox(
            "Target Feature (Optional):",
            options=target_options,
            index=default_target_idx,
            help="Specify a target variable for regression/classification checks or primary KPI tracking.",
            key="context_target_sel",
        )
        target_col = None if chosen_target == "(None / Unsupervised)" else chosen_target

    with col2:
        audience_options = [
            "Executive Leadership",
            "Data Science Team",
            "Finance & Audit",
            "Operations Team",
            "External Clients / Public",
            "General",
        ]
        chosen_audience = st.selectbox(
            "Primary Consumer / Stakeholder:",
            options=audience_options,
            index=audience_options.index(existing_ctx.audience) if existing_ctx.audience in audience_options else 0,
            key="context_audience_sel",
        )

    st.markdown("---")
    st.subheader("3. Domain Detection")

    domain_list = [
        "Finance",
        "Healthcare",
        "E-Commerce",
        "Marketing",
        "HR & Workforce",
        "SaaS & Tech",
        "General",
    ]

    detected_idx = domain_list.index(detected_domain) if detected_domain in domain_list else domain_list.index("General")

    st.info(
        f"🤖 Rule-based domain detected: **{detected_domain}** (Confidence: **{int(confidence * 100)}%** based on column headers)."
    )

    confirmed_domain = st.selectbox(
        "Confirm or override business domain:",
        options=domain_list,
        index=detected_idx,
        key="context_domain_sel",
    )

    st.markdown("---")

    if st.button("💾 Save Context & Generate Action Plan", type="primary", key="save_context_btn"):
        updated_ctx = UserContext(
            goal=selected_goal,
            target_column=target_col,
            audience=chosen_audience,
            domain=confirmed_domain,
            domain_confidence=confidence,
            user_confirmed_domain=True,
        )
        bundle.user_context = updated_ctx
        set_bundle(bundle)
        st.success("Analytical context saved! Navigating to your tailored Action Plan...")
        from ui.pages.registry import get_page_registry
        st.switch_page(get_page_registry()["plan"])

    st.markdown("</div>", unsafe_allow_html=True)
