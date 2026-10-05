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
            st.switch_page("ui/pages/upload.py")
    with col_btn2:
        if st.button(
            "🎲  Try Demo Dataset",
            use_container_width=True,
            key="landing_demo_btn",
        ):
            _load_demo()
            st.rerun()

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
    from core.utils.state import has_dataset

    if not has_dataset():
        _render_landing()
    else:
        # Phase 6 will replace this with the full dashboard
        st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
        st.title("📊 Dashboard")
        st.markdown("---")
        st.info("🚧 Dashboard — Coming in Phase 6")
        st.markdown("</div>", unsafe_allow_html=True)
