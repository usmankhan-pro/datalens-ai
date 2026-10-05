"""
Dashboard page — Landing page when no data is loaded,
main analytics dashboard when data is available.
"""

import streamlit as st


def _load_demo() -> None:
    """Load the synthetic demo dataset into session state."""
    from data.demo.generator import generate_demo_dataset
    from core.utils.state import set_bundle, DatasetBundle, FileMeta

    with st.spinner("Generating demo dataset..."):
        df, _gt = generate_demo_dataset()

        meta = FileMeta(
            name="Synthetic Demo Dataset",
            size_bytes=df.memory_usage(deep=True).sum(),
            rows=len(df),
            cols=len(df.columns),
            extension=".csv",
        )

        bundle = DatasetBundle(
            original_df=df.copy(),
            working_df=df.copy(),
            file_meta=meta,
            is_demo=True,
            load_warnings=["This is a synthetic demo dataset with intentionally injected data quality issues."],
        )
        set_bundle(bundle)


def _render_landing() -> None:
    """Render the landing page when no dataset is loaded."""
    # Hero Section
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)

    st.markdown("", unsafe_allow_html=True)  # spacer
    st.markdown("", unsafe_allow_html=True)

    st.markdown(
        '<h1 class="hero-title">Turn Raw Data Into<br>Reliable Insights.</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p class="hero-subtitle">'
        "Upload your dataset and automatically profile, validate, analyze, "
        "visualize, and understand your data."
        "</p>",
        unsafe_allow_html=True,
    )

    st.markdown("", unsafe_allow_html=True)  # spacer

    # CTA Buttons
    col_btn1, col_btn2, col_spacer = st.columns([1.5, 1.5, 3])
    with col_btn1:
        if st.button(
            "📤  Upload Dataset",
            type="primary",
            use_container_width=True,
            key="landing_upload_btn",
        ):
            from ui.pages.registry import get_page_registry

            st.switch_page(get_page_registry()["upload"])
    with col_btn2:
        if st.button(
            "🎲  Try Demo Dataset",
            use_container_width=True,
            key="landing_demo_btn",
        ):
            _load_demo()
            from ui.pages.registry import get_page_registry

            st.switch_page(get_page_registry()["dashboard"])

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Feature Cards
    st.markdown('<div class="stagger-fade">', unsafe_allow_html=True)
    features = [
        {
            "icon": "🛡️",
            "title": "Data Quality",
            "desc": "Automated quality scoring across 5 dimensions with issue detection and severity classification.",
        },
        {
            "icon": "📊",
            "title": "Statistical Analysis",
            "desc": "Descriptive stats, distributions, confidence intervals, and hypothesis tests with plain-English interpretations.",
        },
        {
            "icon": "🔍",
            "title": "Anomaly Detection",
            "desc": "Multiple detection methods: IQR, Z-score, Modified Z-score, and rolling statistics for time series.",
        },
        {
            "icon": "💡",
            "title": "Actionable Insights",
            "desc": "Generated insights and recommendations backed by real calculations — never fabricated.",
        },
    ]

    cols = st.columns(4)
    for i, feat in enumerate(features):
        with cols[i]:
            st.markdown(
                f"""
                <div class="feature-card">
                    <div class="feature-card-icon">{feat["icon"]}</div>
                    <div class="feature-card-title">{feat["title"]}</div>
                    <div class="feature-card-desc">{feat["desc"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Privacy Notice
    st.markdown(
        """
        <div class="privacy-notice">
            🔒 <span><strong>Your data stays private.</strong>
            All processing happens in memory on the server. No data is stored
            to disk or sent to external services. Session data is fully isolated.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


def page() -> None:
    """Render the Dashboard page."""
    from core.quality import analyze_quality
    from core.insights import build_dashboard_summary
    from core.utils.state import get_bundle, has_dataset

    if not has_dataset():
        _render_landing()
        return

    bundle = get_bundle()
    df = (bundle.working_df if bundle is not None else None) or (bundle.original_df if bundle is not None else None)
    if df is None:
        st.info("No dataset is currently loaded.")
        return

    quality_result = bundle.quality_result if bundle is not None and bundle.quality_result is not None else analyze_quality(df)
    summary = build_dashboard_summary(df, quality_result=quality_result)

    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📊 Executive Dashboard")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rows", f"{summary['rows']:,}")
    with col2:
        st.metric("Columns", f"{summary['cols']}")
    with col3:
        st.metric("Quality", f"{summary['quality_score']:.1f}")
    with col4:
        st.metric("Status", summary['status'].replace('_', ' ').title())

    st.subheader("Executive Summary")
    summary_text = (
        f"This dataset contains {summary['rows']:,} records across {summary['cols']} fields. "
        f"The current quality score is {summary['quality_score']:.1f}, and the staged action plan "
        f"focuses on {len(summary['recommendations'])} prioritized recommendations."
    )
    st.info(summary_text)

    insight_cols = st.columns(min(3, max(1, len(summary['insights']))))
    for idx, insight in enumerate(summary['insights'][:3]):
        with insight_cols[idx % len(insight_cols)]:
            st.markdown(f"### {insight['source_metric']}")
            st.write(insight['text'])

    st.subheader("Priority Recommendations")
    for rec in summary['recommendations'][:5]:
        st.markdown(f"- **{rec['severity']}**: {rec['text']}")

    st.markdown("</div>", unsafe_allow_html=True)
