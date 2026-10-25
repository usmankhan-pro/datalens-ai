"""DataLens AI — Automated Dataset Quality Assessment, Cleaning, and EDA Platform.

Workflow: Upload -> Validate/Profile -> Quality Score -> Clean -> EDA -> Insights -> Export.
Source data is never mutated. All cleaning works on a managed working copy.
"""

from __future__ import annotations

from pathlib import Path
from io import BytesIO
from typing import BinaryIO

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from cleaning import clean_data, count_iqr_outliers
from eda import (
    boxplot,
    categorical_description,
    correlation_heatmap,
    correlations,
    histogram,
    insight_text,
    numeric_description,
    prepare_eda_data,
    value_counts,
)
from plots import available_graphs, figure_png, hue_columns, render_plot, unavailable_reasons

# New modules
from config.settings import (
    QUALITY_WEIGHTS,
    QUALITY_THRESHOLDS,
    MISSING_THRESHOLDS,
    DUPLICATE_THRESHOLDS,
    SCORE_INTERPRETATIONS,
)
from src.quality.quality_score import compute_quality_score, format_quality_report
from src.quality.issue_detection import detect_issues, rank_by_importance
from src.quality.validation import run_all_validations
from src.cleaning.cleaning_pipeline import CleaningPipeline
from src.cleaning.missing_values import detect_missing
from src.cleaning.duplicates import detect_duplicates, preview_duplicates, remove_duplicates
from src.cleaning.data_types import detect_column_types, convert_types
from src.cleaning.outliers import detect_outliers_iqr, detect_outliers_zscore
from src.cleaning.text_cleaning import detect_text_issues, clean_text
from src.analysis.descriptive import dataset_overview, all_column_profiles
from src.analysis.recommendations import generate_insights, recommendations_for_cleaning
from src.analysis.correlation import pairwise_correlations, strong_correlations
from src.visualization.charts import (
    histogram as plotly_histogram,
    box_plot as plotly_box,
    bar_chart as plotly_bar,
    scatter_plot as plotly_scatter,
    line_chart as plotly_line,
    heatmap as plotly_heatmap,
    missingness_bar as plotly_missingness,
    quality_score_gauge as plotly_gauge,
)
from src.visualization.chart_selector import recommend_charts, recommend_pair_chart, recommend_correlation_chart
from src.reporting.report_generator import build_quality_report, build_cleaning_report, build_full_report
from src.reporting.export_manager import (
    export_cleaned_dataset,
    export_cleaning_log,
    export_quality_report as export_quality_csv,
)
from src.utils.formatting import format_pct, format_count, format_bytes, format_score, format_number
from src.data.schema_detector import detect_schema

DEMO_PATH = Path(__file__).parent / "data" / "telco_churn.csv"


# ---------------------------------------------------------------------------
# Existing functions (preserved for backward compatibility)
# ---------------------------------------------------------------------------

def csv_bytes(data: pd.DataFrame) -> bytes:
    return data.to_csv(index=False).encode("utf-8")


def excel_bytes(data: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    data.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def log_csv_bytes(records: list[dict[str, object]]) -> bytes:
    columns = ["step", "column", "rows_affected"]
    return pd.DataFrame(records, columns=columns).to_csv(index=False).encode("utf-8")


def read_table(source: BinaryIO, filename: str) -> pd.DataFrame:
    extension = Path(filename).suffix.lower()
    if extension == ".csv":
        try:
            data = pd.read_csv(source, dtype={"TotalCharges": str}, skipinitialspace=True)
        except pd.errors.EmptyDataError as error:
            raise ValueError("The uploaded CSV is empty.") from error
        return normalize_blank_cells(data)
    if extension in {".xlsx", ".xlsm"}:
        data = pd.read_excel(source, dtype={"TotalCharges": str}, engine="openpyxl")
        return normalize_blank_cells(data)
    raise ValueError("Choose a CSV or Excel file.")


def normalize_blank_cells(data: pd.DataFrame) -> pd.DataFrame:
    return data.replace(r"^\s*$", pd.NA, regex=True)


def load_demo() -> pd.DataFrame:
    data = pd.read_csv(DEMO_PATH, dtype={"TotalCharges": str}, skipinitialspace=True)
    return normalize_blank_cells(data)


def show_overview(data: pd.DataFrame) -> None:
    memory = int(data.memory_usage(index=True, deep=True).sum())
    st.metric("Rows", f"{len(data):,}")
    st.metric("Columns", f"{len(data.columns):,}")
    st.metric("Duplicates", f"{int(data.duplicated().sum()):,}")
    st.metric("Memory usage", f"{memory:,} bytes")
    st.subheader("Column details")
    st.dataframe(pd.DataFrame({"dtype": data.dtypes.astype(str), "missing": data.isna().sum()}))
    st.subheader("First rows")
    st.dataframe(data.head())


def data_summary(data: pd.DataFrame, label: str) -> dict[str, int | str]:
    return {
        "dataset": label,
        "rows": len(data),
        "missing cells": int(data.isna().sum().sum()),
        "duplicates": int(data.duplicated().sum()),
    }


def cleaning_controls(data: pd.DataFrame) -> tuple[dict[str, bool], dict[str, tuple[str, str]], dict[str, str]]:
    labels = ["Remove duplicates", "Fix types", "Strip whitespace and unify case", "Handle missing values", "Handle IQR outliers"]
    keys = ["duplicates", "types", "text", "missing", "outliers"]
    enabled = {key: st.checkbox(label, key=f"clean_{key}") for key, label in zip(keys, labels)}
    missing_rules: dict[str, tuple[str, str]] = {}
    outlier_rules: dict[str, str] = {}
    if enabled["missing"]:
        for column in data.columns[data.isna().any()]:
            methods = ["Drop rows", "Mode", "Custom"]
            if pd.api.types.is_numeric_dtype(data[column]):
                methods[1:1] = ["Median", "Mean"]
            method = st.selectbox(f"Missing values: {column}", methods, key=f"missing_{column}")
            custom = st.text_input(f"Custom value: {column}", key=f"custom_{column}") if method == "Custom" else ""
            missing_rules[column] = (method, custom)
    if enabled["outliers"]:
        for column in data.select_dtypes(include="number").columns:
            st.caption(f"{column}: {count_iqr_outliers(data, column):,} IQR outliers")
            outlier_rules[column] = st.selectbox(f"IQR action: {column}", ["Ignore", "Cap", "Remove"], key=f"outlier_{column}")
    return enabled, missing_rules, outlier_rules


def show_cleaning(data: pd.DataFrame) -> None:
    st.subheader("Cleaning steps")
    enabled, missing_rules, outlier_rules = cleaning_controls(data)
    cleaned, log = clean_data(data, enabled, missing_rules, outlier_rules)
    st.session_state["cleaned_data"] = cleaned
    st.session_state["cleaning_log"] = log
    st.subheader("Before and after")
    st.dataframe(pd.DataFrame([data_summary(data, "Before"), data_summary(cleaned, "After")]).set_index("dataset"))
    if log:
        st.subheader("Cleaning log")
        st.dataframe(pd.DataFrame(log))
    else:
        st.info("Select a cleaning step to preview its effect.")
    st.subheader("Cleaned preview")
    st.dataframe(cleaned.head())
    st.subheader("Downloads")
    st.download_button("Download cleaned CSV", csv_bytes(cleaned), "cleaned_data.csv", "text/csv")
    st.download_button(
        "Download cleaned Excel",
        excel_bytes(cleaned),
        "cleaned_data.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    st.download_button("Download cleaning log", log_csv_bytes(log), "cleaning_log.csv", "text/csv")


def show_eda(data: pd.DataFrame) -> None:
    analysis = prepare_eda_data(st.session_state.get("cleaned_data", data))
    numeric_columns = list(analysis.select_dtypes(include="number").columns)
    categorical_columns = list(analysis.select_dtypes(include=["object", "string", "category"]).columns)
    st.subheader("Computed insights")
    for insight in insight_text(analysis):
        st.write(f"- {insight}")
    st.subheader("Numeric description")
    st.dataframe(numeric_description(analysis))
    st.subheader("Categorical description")
    st.dataframe(categorical_description(analysis))
    st.subheader("Missing values")
    st.dataframe(analysis.isna().sum().rename("missing").to_frame())
    if categorical_columns:
        column = st.selectbox("Value counts", categorical_columns, key="eda_value_counts")
        st.dataframe(value_counts(analysis, column).rename("count").to_frame())
    if numeric_columns:
        column = st.selectbox("Numeric distribution", numeric_columns, key="eda_numeric_column")
        st.pyplot(histogram(analysis, column))
        st.pyplot(boxplot(analysis, column))
    if len(numeric_columns) >= 2:
        st.subheader("Correlation matrix")
        st.dataframe(correlations(analysis))
        st.pyplot(correlation_heatmap(analysis))


def show_visualize(data: pd.DataFrame) -> None:
    analysis = prepare_eda_data(st.session_state.get("cleaned_data", data))
    x, y, graph, hue = visualization_options(analysis)
    if not graph:
        return
    figure = render_plot(analysis, x, graph, y, hue)
    png = figure_png(figure)
    st.pyplot(figure)
    st.download_button(
        "Download PNG",
        data=png,
        file_name=f"{graph.lower().replace(' ', '_')}_{x}.png",
        mime="image/png",
        icon=":material/download:",
    )
    plt.close(figure)


def visualization_options(data: pd.DataFrame) -> tuple[str, str | None, str | None, str | None]:
    x = st.selectbox("X axis", data.columns, key="visual_x")
    y_options = ["No Y axis", *[column for column in data.columns if column != x]]
    y_choice = st.selectbox("Y axis (optional)", y_options, key="visual_y")
    y = None if y_choice == "No Y axis" else y_choice
    graphs = available_graphs(data, x, y)
    with st.expander("Why other graph types are unavailable"):
        for reason in unavailable_reasons(data, x, y).values():
            st.write(reason)
    if not graphs:
        st.info("This axis selection has no compatible graph. Choose a numeric Y for a date column.")
        return x, y, None, None
    graph = st.selectbox("Graph type", graphs, key="visual_graph")
    hues = hue_columns(data, x, y, graph)
    hue_choice = st.selectbox("Hue (optional)", ["None", *hues], key="visual_hue")
    hue = None if hue_choice == "None" else hue_choice
    return x, y, graph, hue


# ---------------------------------------------------------------------------
# New: Quality Assessment tab
# ---------------------------------------------------------------------------

def show_quality_assessment(data: pd.DataFrame) -> None:
    st.subheader("Dataset Quality Assessment")
    st.caption("Transparent 0-100 score based on five measured dimensions. Weights are configurable in config/settings.py.")

    result = compute_quality_score(data)

    # Overall score gauge
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.plotly_chart(plotly_gauge(result.overall_score), use_container_width=True)

    st.metric("Quality Score", format_score(result.overall_score))
    st.metric("Interpretation", result.overall_label)
    st.info(result.overall_interpretation)
    st.caption(result.overall_recommendation)

    # Dimension breakdown
    st.subheader("Dimension Breakdown")
    dim_data = []
    for d in format_quality_report(result):
        dim_data.append({
            "Dimension": d["dimension"],
            "Weight": f"{d['weight']}%",
            "Score": format_score(d["score"]),
            "Severity": d["severity"],
            "Numerator": format_count(d["numerator"]) if d["numerator"] is not None else "n/a",
            "Denominator": format_count(d["denominator"]) if d["denominator"] is not None else "n/a",
            "Effect on Overall": format_number(d["effect_on_overall"]),
        })
    st.dataframe(pd.DataFrame(dim_data), use_container_width=True)

    if result.excluded_dimensions:
        st.warning(f"Dimensions not assessed: {', '.join(result.excluded_dimensions)}")

    # Issues
    st.subheader("Quality Issues Ranked by Importance")
    findings = rank_by_importance(detect_issues(data))
    if findings:
        finding_data = []
        for f in findings:
            finding_data.append({
                "Severity": f["severity"],
                "Column": f["column"],
                "Title": f["title"],
                "Detail": f["detail"],
                "Suggestion": f["suggestion"],
            })
        st.dataframe(pd.DataFrame(finding_data), use_container_width=True)
    else:
        st.success("No quality issues detected.")

    # Recommendations
    st.subheader("Cleaning Recommendations")
    recs = recommendations_for_cleaning(data, result)
    if recs:
        for r in recs:
            badge = "HIGH" if r["priority"] == "HIGH" else "MEDIUM"
            st.write(f"**[{badge}]** {r['dimension']}: {r['action']}")
    else:
        st.info("No cleaning recommendations at this time.")


# ---------------------------------------------------------------------------
# New: Cleaning Studio tab (with audit trail and undo/reset)
# ---------------------------------------------------------------------------

def _get_pipeline() -> CleaningPipeline:
    if "cleaning_pipeline" not in st.session_state:
        data = st.session_state.get("data")
        if data is None:
            return None
        st.session_state["cleaning_pipeline"] = CleaningPipeline(data)
    return st.session_state["cleaning_pipeline"]


def show_cleaning_studio(data: pd.DataFrame) -> None:
    st.subheader("Cleaning Studio")
    st.caption("Preview every change before applying. The original uploaded data is never modified.")

    pipeline = _get_pipeline()
    if pipeline is None:
        st.error("No dataset loaded. Upload a dataset first.")
        return

    working = pipeline.working
    source = pipeline.source

    # Status
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Original rows", f"{len(source):,}")
    with col2:
        st.metric("Working rows", f"{len(working):,}")
    with col3:
        st.metric("Operations applied", f"{len(pipeline.records)}")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Reset to original", key="clean_reset", disabled=not pipeline.can_undo):
            pipeline.reset()
            st.rerun()
    with col_b:
        if st.button("Undo last operation", key="clean_undo", disabled=not pipeline.can_undo):
            pipeline.undo()
            st.rerun()

    st.divider()

    # Step 1: Duplicates
    st.markdown("### 1. Duplicate Rows")
    dup_report = pipeline.duplicate_report()
    st.write(f"{dup_report['n_duplicate_rows']:,} duplicate rows ({dup_report['duplicate_pct']}%)")
    if dup_report["n_duplicate_rows"] > 0:
        st.dataframe(pipeline.duplicate_preview(max_rows=10), use_container_width=True)
        keep = st.selectbox("Keep occurrence", ["first", "last"], key="dup_keep")
        subset_cols = st.multiselect("Columns to match (blank = all columns)", working.columns.tolist(), key="dup_subset")
        if st.button("Remove duplicates", key="dup_remove"):
            records = pipeline.remove_duplicates(subset=subset_cols if subset_cols else None, keep=keep)
            st.success(f"Removed {records[0]['rows_affected']} duplicate row(s).")
            st.rerun()
    else:
        st.info("No duplicate rows detected.")

    st.divider()

    # Step 2: Data types
    st.markdown("### 2. Data Types")
    types_report = pipeline.profile_columns()
    conv_cols = {}
    for col_name, info in types_report.items():
        inferred = info.get("inferred_type", "unknown")
        if inferred in ("numeric_string", "date_string"):
            st.write(f"**{col_name}**: stored as {info['current_dtype']}, likely {inferred} (confidence {info['confidence']})")
            target = st.selectbox(f"Convert {col_name} to", ["numeric", "datetime", "string", "categorical"], key=f"conv_{col_name}")
            conv_cols[col_name] = target
    if conv_cols and st.button("Apply type conversions", key="conv_apply"):
        records = pipeline.fix_types(conv_cols)
        st.success(f"Converted {len(records)} column(s).")
        st.rerun()

    st.divider()

    # Step 3: Missing values
    st.markdown("### 3. Missing Values")
    missing_report = detect_missing(working)
    missing_cols = {c: v for c, v in missing_report.items() if v["n_missing"] > 0}
    if missing_cols:
        for col_name, stats in missing_cols.items():
            st.write(f"**{col_name}**: {stats['n_missing']:,} missing ({stats['missing_pct']}%)")
            methods = ["Drop rows", "Mode", "Custom"]
            if pd.api.types.is_numeric_dtype(working[col_name]):
                methods[1:1] = ["Median", "Mean"]
            method = st.selectbox(f"Strategy for {col_name}", methods, key=f"miss_{col_name}")
            custom = ""
            if method == "Custom":
                custom = st.text_input(f"Custom value for {col_name}", key=f"miss_custom_{col_name}")
            if st.button(f"Apply to {col_name}", key=f"miss_apply_{col_name}"):
                rules = {col_name: (method, custom)}
                records = pipeline.fill_missing(rules)
                st.success(f"Filled {stats['n_missing']:,} missing value(s) in {col_name}.")
                st.rerun()
    else:
        st.info("No missing values detected.")

    st.divider()

    # Step 4: Text cleaning
    st.markdown("### 4. Text Cleaning")
    text_issues = pipeline.text_issues()
    if text_issues:
        text_rules = {}
        for col_name, info in text_issues.items():
            if info.get("issues"):
                st.write(f"**{col_name}**: {', '.join(info['issues'])}")
                trim = st.checkbox("Trim whitespace", value=True, key=f"text_trim_{col_name}")
                collapse = st.checkbox("Collapse spaces", value=True, key=f"text_collapse_{col_name}")
                case = st.selectbox("Case", ["none", "lower", "upper", "title"], key=f"text_case_{col_name}")
                text_rules[col_name] = {"trim": trim, "collapse_spaces": collapse, "case": case}
        if text_rules and st.button("Apply text cleaning", key="text_apply"):
            records = pipeline.clean_text(text_rules)
            st.success(f"Cleaned {len(text_rules)} column(s).")
            st.rerun()
    else:
        st.info("No text-quality issues detected.")

    st.divider()

    # Step 5: Outliers
    st.markdown("### 5. Outlier Analysis")
    numeric_cols = working.select_dtypes(include="number").columns.tolist()
    outlier_rules = {}
    for col_name in numeric_cols:
        report = pipeline.outlier_report_iqr(col_name)
        n_out = report["n_outliers"]
        if n_out > 0:
            st.write(f"**{col_name}**: {n_out} IQR outliers")
            action = st.selectbox(f"Action for {col_name}", ["Ignore", "Cap", "Remove", "Flag"], key=f"out_{col_name}")
            if action != "Ignore":
                outlier_rules[col_name] = {"method": "iqr", "action": action.lower(), "multiplier": 1.5}
    if outlier_rules and st.button("Apply outlier handling", key="out_apply"):
        records = pipeline.handle_outliers(outlier_rules)
        st.success(f"Handled outliers in {len(outlier_rules)} column(s).")
        st.rerun()
    elif not numeric_cols:
        st.info("No numeric columns for outlier analysis.")

    st.divider()

    # Audit trail
    st.markdown("### Cleaning Audit Trail")
    if pipeline.records:
        audit_df = pd.DataFrame([r.to_dict() for r in pipeline.records])
        st.dataframe(audit_df, use_container_width=True)
        csv_log = audit_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download cleaning audit log", csv_log, "cleaning_audit_log.csv", "text/csv")
    else:
        st.info("No cleaning operations applied yet.")

    # Working copy preview
    st.markdown("### Working Copy Preview")
    st.dataframe(working.head(20), use_container_width=True)

    # Store cleaned data for other tabs
    st.session_state["cleaned_data"] = working
    st.session_state["cleaning_log"] = [r.to_dict() for r in pipeline.records]


# ---------------------------------------------------------------------------
# New: EDA tab with Plotly
# ---------------------------------------------------------------------------

def show_eda_modern(data: pd.DataFrame) -> None:
    st.subheader("Exploratory Data Analysis")
    analysis = st.session_state.get("cleaned_data", data)

    overview = dataset_overview(analysis)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rows", format_count(overview["n_rows"]))
    with col2:
        st.metric("Columns", format_count(overview["n_cols"]))
    with col3:
        st.metric("Missing cells", format_count(overview["n_missing_cells"]))
    with col4:
        st.metric("Duplicates", format_count(overview["n_duplicates"]))

    # Missingness chart
    st.plotly_chart(plotly_missingness(analysis), use_container_width=True)

    # Column selection for detailed profiling
    st.markdown("### Column Profiles")
    all_profiles = all_column_profiles(analysis)
    selected_col = st.selectbox("Select column for detailed profile", [""] + list(analysis.columns), key="eda_profile_col")
    if selected_col and selected_col in all_profiles:
        prof = all_profiles[selected_col]
        st.write(f"**Type**: {prof['dtype']} | **Missing**: {prof['n_missing']} ({prof['missing_pct']}%) | **Unique**: {prof['n_unique']}")
        if prof["is_numeric"]:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(plotly_histogram(analysis, selected_col), use_container_width=True)
            with c2:
                st.plotly_chart(plotly_box(analysis, selected_col), use_container_width=True)
            st.json({k: v for k, v in prof.items() if k in ("min", "max", "mean", "median", "std", "q1", "q3", "iqr", "skewness")})
        elif prof["is_datetime"]:
            st.write(f"Date range: {prof.get('date_min', 'n/a')} to {prof.get('date_max', 'n/a')}")
        else:
            st.plotly_chart(plotly_bar(analysis, selected_col), use_container_width=True)
            st.json({"top_categories": prof.get("top_categories", {})})

    # Bivariate
    st.markdown("### Bivariate Analysis")
    col_a = st.selectbox("Column A", analysis.columns, key="bivar_a")
    col_b = st.selectbox("Column B", [c for c in analysis.columns if c != col_a], key="bivar_b")
    pair_recs = recommend_pair_chart(analysis, col_a, col_b)
    if pair_recs:
        for rec in pair_recs:
            chart_type = rec["chart_type"]
            x = rec.get("x", col_a)
            y = rec.get("y", col_b)
            if chart_type == "scatter_plot":
                st.plotly_chart(plotly_scatter(analysis, x, y), use_container_width=True)
            elif chart_type == "line_chart":
                cat_col = rec.get("category_column")
                st.plotly_chart(plotly_line(analysis, x, y, color_column=cat_col), use_container_width=True)
            elif chart_type == "box_plot":
                st.plotly_chart(plotly_box(analysis, y, category_column=x), use_container_width=True)

    # Correlation
    st.markdown("### Correlation Matrix")
    corr_rec = recommend_correlation_chart(analysis)
    if corr_rec["recommended"]:
        method = st.selectbox("Correlation method", ["pearson", "spearman"], key="corr_method")
        corr_result = pairwise_correlations(analysis, method=method)
        coeffs = corr_result["coefficients"]
        corr_df = pd.DataFrame(coeffs)
        st.plotly_chart(plotly_heatmap(corr_df, title=f"{method.title()} Correlation Matrix"), use_container_width=True)
        strong = strong_correlations(analysis, threshold=0.7, method=method)
        if strong:
            st.write("**Strong correlations (|r| >= 0.7):**")
            for p in strong:
                st.write(f"- {p['column_a']} vs {p['column_b']}: r = {p['correlation']} (n = {p['n_samples']})")
        st.caption("Correlation does not imply causation.")
    else:
        st.info(corr_rec["reason"])


# ---------------------------------------------------------------------------
# New: Insights and Recommendations tab
# ---------------------------------------------------------------------------

def show_insights(data: pd.DataFrame) -> None:
    st.subheader("Insights and Recommendations")
    result = compute_quality_score(data)
    insights = generate_insights(data, result)

    # Group by category
    categories = {}
    for ins in insights:
        cat = ins["category"]
        categories.setdefault(cat, []).append(ins)

    for cat in ["Observed fact", "Statistical interpretation", "Suggested action"]:
        items = categories.get(cat, [])
        if items:
            with st.expander(f"{cat} ({len(items)})", expanded=True):
                for ins in items:
                    st.markdown(f"**{ins['title']}**")
                    st.write(ins["observation"])
                    st.caption(f"Evidence: {ins['evidence']}")
                    st.write(f"Why it matters: {ins['why_it_matters']}")
                    st.write(f"Recommended action: {ins['recommended_action']}")
                    st.caption(f"Limitation: {ins['limitation']}")
                    st.divider()


# ---------------------------------------------------------------------------
# New: Export tab
# ---------------------------------------------------------------------------

def show_export(data: pd.DataFrame) -> None:
    st.subheader("Export Results")
    cleaned = st.session_state.get("cleaned_data", data)
    log = st.session_state.get("cleaning_log", [])
    quality_result = compute_quality_score(cleaned)

    st.markdown("### Download Cleaned Dataset")
    fmt = st.selectbox("Format", ["csv", "excel"], key="export_fmt")
    file_bytes, file_name, mime = export_cleaned_dataset(cleaned, fmt)
    st.download_button(f"Download cleaned dataset ({fmt.upper()})", file_bytes, file_name, mime)

    st.markdown("### Download Cleaning Audit Log")
    if log:
        log_bytes, log_name, log_mime = export_cleaning_log(log)
        st.download_button("Download cleaning log (CSV)", log_bytes, log_name, log_mime)
    else:
        st.info("No cleaning operations recorded yet.")

    st.markdown("### Download Quality Report")
    dim_data = format_quality_report(quality_result)
    q_bytes, q_name, q_mime = export_quality_csv(dim_data)
    st.download_button("Download quality report (CSV)", q_bytes, q_name, q_mime)

    st.markdown("### Before / After Summary")
    before_score = compute_quality_score(data)
    after_score = compute_quality_score(cleaned)
    summary = pd.DataFrame([
        {"Stage": "Original", "Rows": len(data), "Columns": len(data.columns), "Quality Score": before_score.overall_score},
        {"Stage": "Cleaned", "Rows": len(cleaned), "Columns": len(cleaned.columns), "Quality Score": after_score.overall_score},
    ])
    st.dataframe(summary, use_container_width=True)
    st.caption("Score change is only meaningful if recalculated with the same methodology.")


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def show_dataset_tabs(data: pd.DataFrame) -> None:
    overview, quality, cleaning, eda_modern, insights, export, visualize = st.tabs([
        "Overview", "Quality", "Cleaning Studio", "EDA", "Insights", "Export", "Visualize"
    ])
    with overview:
        show_overview(data)
    with quality:
        show_quality_assessment(data)
    with cleaning:
        show_cleaning_studio(data)
    with eda_modern:
        show_eda_modern(data)
    with insights:
        show_insights(data)
    with export:
        show_export(data)
    with visualize:
        show_visualize(data)


def main() -> None:
    st.set_page_config(page_title="DataLens AI", page_icon="📊", layout="wide")
    st.sidebar.title("DataLens AI")
    st.title("DataLens AI")

    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Source")
    uploaded = st.sidebar.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xlsm"])
    if uploaded is not None:
        try:
            st.session_state["data"] = read_table(uploaded, uploaded.name)
            st.session_state["source"] = uploaded.name
            st.session_state.pop("cleaning_pipeline", None)
            st.sidebar.success(f"Loaded {uploaded.name}")
        except (ValueError, pd.errors.ParserError, OSError) as error:
            st.sidebar.error(str(error))

    if st.sidebar.button("Use demo data (Telco churn)", icon=":material/table_view:"):
        st.session_state["data"] = load_demo()
        st.session_state["source"] = "Telco customer churn demo"
        st.session_state.pop("cleaning_pipeline", None)

    if "data" in st.session_state:
        st.sidebar.caption(f"Dataset: {st.session_state['source']}")
        st.sidebar.caption(f"Rows: {len(st.session_state['data']):,} | Cols: {len(st.session_state['data'].columns):,}")
        show_dataset_tabs(st.session_state["data"])
    else:
        st.info("Upload a dataset or choose the Telco demo to begin.")


if __name__ == "__main__":
    main()
