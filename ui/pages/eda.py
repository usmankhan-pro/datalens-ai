"""EDA (Exploratory Data Analysis) UI page for DataLens AI."""

import streamlit as st
import pandas as pd

from core.eda import (
    compute_bivariate_analysis,
    compute_eda_overview,
    compute_missing_patterns,
    compute_outlier_analysis,
    compute_target_analysis,
    compute_time_trends,
    compute_top_insights,
    compute_univariate_analysis,
)
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Exploratory Data Analysis page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📈 Exploratory Data Analysis (EDA)")
    st.caption("Deep-dive exploration of the cleaned dataset. Every metric is computed strictly from real DataFrame data.")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📈</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload and clean a dataset to explore distributions, correlations, and insights.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for EDA.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = bundle.working_df

    # Target column selector (persists in session state or from UserContext)
    user_target = getattr(bundle.user_context, "target_column", None) if hasattr(bundle, "user_context") and bundle.user_context else None
    col_options = ["None"] + list(df.columns)
    default_idx = col_options.index(user_target) if user_target in col_options else 0

    c_sel1, c_sel2 = st.columns([3, 1])
    with c_sel1:
        target_selection = st.selectbox(
            "🎯 Target Variable (Optional - enables target predictive analysis):",
            col_options,
            index=default_idx,
            key="eda_target_selector",
        )
    target_col = None if target_selection == "None" else target_selection

    with c_sel2:
        st.write("")
        st.caption(f"**Shape:** {len(df):,} rows × {len(df.columns)} cols")

    st.markdown("---")

    # 1. Top 5 Plain-Language Insights
    st.subheader("💡 Top 5 Plain-Language Insights")
    insights = compute_top_insights(df, target_col=target_col)
    if insights:
        for idx, ins in enumerate(insights, start=1):
            cat_badge = ins.get("category", "General")
            text = ins.get("text", "")
            st.markdown(
                f"""
                <div class="datalens-card" style="padding: 0.85rem 1.25rem; margin-bottom: 0.65rem; border-left: 4px solid var(--primary, #3b82f6);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.25rem;">
                        <span style="font-weight: 700; font-size: 0.85rem; color: var(--primary, #3b82f6);">{idx}. {cat_badge}</span>
                    </div>
                    <div style="font-size: 0.95rem; line-height: 1.45; color: var(--text, #1e293b);">{text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No insights computed for the current dataset.")

    st.markdown("---")

    # Tabs for in-depth EDA
    tabs = st.tabs([
        "📋 Overview",
        "📊 Univariate",
        "🔲 Missing Patterns",
        "🎯 Outliers",
        "🔗 Bivariate & Correlations",
        "🎯 Target Analysis",
        "📈 Time Trends",
    ])

    # Tab 1: Overview
    with tabs[0]:
        overview = compute_eda_overview(df)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Rows", f"{overview['rows']:,}")
        m2.metric("Columns", f"{overview['cols']}")
        m3.metric("Memory Usage", f"{overview['memory_mb']} MB")
        m4.metric("Missing %", f"{overview['missing_pct']}%")
        m5.metric("Duplicates", f"{overview['duplicate_rows']:,}")

        st.markdown("**Column Types Breakdown:**")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("Numeric", overview["col_types"]["numeric"])
        tc2.metric("Categorical/Text", overview["col_types"]["categorical"])
        tc3.metric("DateTime", overview["col_types"]["datetime"])
        tc4.metric("Boolean", overview["col_types"]["boolean"])

        with st.expander("Preview Dataset Head (First 15 Rows)", expanded=False):
            st.dataframe(df.head(15), width="stretch")

    # Tab 2: Univariate
    with tabs[1]:
        uni = compute_univariate_analysis(df)
        num_stats = uni.get("numeric", {})
        cat_stats = uni.get("categorical", {})

        if num_stats:
            st.markdown("##### Numeric Distributions")
            num_rows = []
            for col, s in num_stats.items():
                num_rows.append({
                    "Column": col,
                    "Count": s["count"],
                    "Missing": s["missing"],
                    "Mean": s["mean"],
                    "Std": s["std"],
                    "Min": s["min"],
                    "25%": s["q25"],
                    "Median": s["median"],
                    "75%": s["q75"],
                    "Max": s["max"],
                    "Skewness": s["skewness"],
                })
            st.dataframe(pd.DataFrame(num_rows), width="stretch", hide_index=True)

        if cat_stats:
            st.markdown("##### Categorical Cardinality & Top Modes")
            cat_rows = []
            for col, s in cat_stats.items():
                cat_rows.append({
                    "Column": col,
                    "Count": s["count"],
                    "Unique (Cardinality)": s["unique"],
                    "Top Value (Mode)": s["mode"],
                    "Top Value Frequency": s["top_freq"],
                    "Top Value %": f"{s['top_pct']}%",
                })
            st.dataframe(pd.DataFrame(cat_rows), width="stretch", hide_index=True)

    # Tab 3: Missing Patterns
    with tabs[2]:
        miss = compute_missing_patterns(df)
        col_miss = miss.get("column_missing", {})
        miss_data = [{"Column": k, "Missing Count": v["count"], "Missing %": f"{v['pct']}%"} for k, v in col_miss.items()]
        st.dataframe(pd.DataFrame(miss_data), width="stretch", hide_index=True)

        co_occ = miss.get("co_occurrence", [])
        if co_occ:
            st.markdown("##### Missing Co-Occurrence (Pairs Missing Together)")
            st.dataframe(pd.DataFrame(co_occ), width="stretch", hide_index=True)

        st.markdown("##### Row Missingness Distribution")
        st.json(miss.get("row_missing_distribution", {}))

    # Tab 4: Outliers
    with tabs[3]:
        outliers = compute_outlier_analysis(df, factor=1.5)
        if outliers:
            outlier_rows = []
            for col, o in outliers.items():
                outlier_rows.append({
                    "Column": col,
                    "IQR Outlier Count": o["iqr_count"],
                    "IQR Outlier %": f"{o['iqr_pct']}%",
                    "Lower Fence": o["lower_fence"],
                    "Upper Fence": o["upper_fence"],
                    "Z-Score (|z|>3) Count": o["z_count"],
                    "Min Extreme": o["min_outlier"],
                    "Median": o["median"],
                    "Max Extreme": o["max_outlier"],
                })
            st.dataframe(pd.DataFrame(outlier_rows), width="stretch", hide_index=True)
        else:
            st.info("No numeric columns available for outlier analysis.")

    # Tab 5: Bivariate & Correlations
    with tabs[4]:
        biv = compute_bivariate_analysis(df, min_group_size=5)
        p_matrix = biv.get("pearson", {})
        s_matrix = biv.get("spearman", {})

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Pearson Correlation Matrix (Linear)")
            if p_matrix:
                st.dataframe(pd.DataFrame(p_matrix), width="stretch")
            else:
                st.info("Need at least 2 numeric columns for Pearson correlation.")

        with c2:
            st.markdown("##### Spearman Rank Correlation Matrix (Monotonic)")
            if s_matrix:
                st.dataframe(pd.DataFrame(s_matrix), width="stretch")
            else:
                st.info("Need at least 2 numeric columns for Spearman correlation.")

        st.markdown("##### Group Comparisons (Min 5 observations per group)")
        grp_comps = biv.get("group_comparisons", [])
        if grp_comps:
            for g in grp_comps:
                sig_badge = "✅ Significant (p < 0.05)" if g["is_statistically_significant"] else "ℹ️ Not Significant"
                with st.expander(f"`{g['numeric_col']}` grouped by `{g['categorical_col']}` — {sig_badge}"):
                    st.caption(f"F-statistic: {g['f_statistic']}, p-value: {g['p_value']}, Groups: {g['groups_compared']}")
                    st.dataframe(pd.DataFrame(g["group_stats"]), width="stretch", hide_index=True)
        else:
            st.caption(r"No eligible pairs of categorical and numeric columns with $\ge 5$ observations per group.")

    # Tab 6: Target Analysis
    with tabs[5]:
        if not target_col:
            st.info("Select a target column using the selector above to unlock goal-aware target analysis.")
        else:
            t_data = compute_target_analysis(df, target_col, min_group_size=5)
            st.markdown(f"##### Target Analysis for `{target_col}` ({t_data.get('target_type')})")
            if "class_balance" in t_data:
                cb_rows = [{"Class": k, "Count": v["count"], "Percentage": f"{v['pct']}%"} for k, v in t_data["class_balance"].items()]
                st.dataframe(pd.DataFrame(cb_rows), width="stretch", hide_index=True)
                st.write(f"**Imbalance Ratio:** {t_data.get('imbalance_ratio')}:1")
                if t_data.get("is_imbalanced"):
                    st.warning("⚠️ High class imbalance detected (> 3:1). Recommendation: consider stratified sampling or reweighting.")
            elif "correlations" in t_data:
                st.dataframe(pd.DataFrame(t_data["correlations"]), width="stretch", hide_index=True)

    # Tab 7: Time Trends
    with tabs[6]:
        trends = compute_time_trends(df)
        if trends:
            st.markdown(f"##### Time Trend Analysis (`{trends.get('date_column')}`)")
            st.write(f"Span: {trends.get('span_days')} days ({trends.get('min_date')} to {trends.get('max_date')})")
            counts = trends.get("period_counts", {})
            if counts:
                trend_df = pd.DataFrame([{"Period": k, "Record Count": v} for k, v in counts.items()])
                st.dataframe(trend_df, width="stretch", hide_index=True)
        else:
            st.info("No datetime columns detected in the working dataset.")

    st.markdown("</div>", unsafe_allow_html=True)
