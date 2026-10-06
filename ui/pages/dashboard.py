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
            width="stretch",
            key="home_upload_btn",
        ):
            st.session_state["home_show_uploader"] = True
            st.rerun()
    with col_btn2:
        if st.button(
            "🎲  Try Demo Dataset",
            width="stretch",
            key="home_demo_btn",
        ):
            _load_demo()
            from ui.pages.registry import get_page_registry

            st.switch_page(get_page_registry()["overview"])

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
    import pandas as pd

    from core.anomaly import detect_anomalies
    from core.insights import build_dashboard_summary
    from core.kpi import detect_kpis
    from core.quality import analyze_quality
    from core.statistics import correlation_matrix
    from core.trends import analyze_trends
    from core.utils.state import get_bundle, has_dataset

    if not has_dataset():
        _render_landing()
        return

    bundle = get_bundle()
    df = None
    if bundle is not None:
        df = bundle.working_df if bundle.working_df is not None else bundle.original_df
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

        st.subheader("Key Performance Indicators")
        kpis = detect_kpis(df)
        if kpis:
            kpi_cols = st.columns(min(3, len(kpis)))
            for idx, kpi in enumerate(kpis[:3]):
                with kpi_cols[idx % len(kpi_cols)]:
                    value = kpi["value"]
                    display_value = f"{value:.2f}%" if kpi.get("unit") == "percent" else f"{value:,.2f}"
                    st.metric(kpi["name"], display_value)
        else:
            st.info("No KPI candidates were identified.")

        st.subheader("Trend")
        date_columns = [
            column for column in df.columns
            if pd.api.types.is_datetime64_any_dtype(df[column]) or "date" in str(column).lower()
        ]
        numeric_columns = df.select_dtypes(include=["number"]).columns.tolist()
        trend = None
        if date_columns and numeric_columns:
            trend = analyze_trends(df, date_columns[0], numeric_columns[0], freq="ME")
        if trend and trend.get("status") == "ok":
            st.write(trend["summary"])
        else:
            st.info("Insufficient date and numeric data for a trend summary.")

        st.subheader("Top Potential Anomalies")
        anomalies = detect_anomalies(df, method="iqr")
        if anomalies:
            anomaly_df = pd.DataFrame(anomalies).sort_values("score", ascending=False).head(5)
            st.dataframe(anomaly_df, width="stretch", hide_index=True)
        else:
            st.info("No potential anomalies were identified by the IQR method.")

        st.subheader("Correlations")
        if len(numeric_columns) >= 2:
            correlations = correlation_matrix(df)["pearson"]
            st.dataframe(correlations, width="stretch")
            st.caption("Correlation does not imply causation.")
        else:
            st.info("At least two numeric columns are required for correlations.")

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
