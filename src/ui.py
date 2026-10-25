"""Dedicated Streamlit workspaces for the DataFlow Analytics application."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis.bivariate import analyze_pair
from src.analysis.correlation import pairwise_correlations
from src.analysis.descriptive import all_column_profiles, column_profile, dataset_overview
from src.analysis.recommendations import generate_insights, recommendations_for_cleaning
from src.analysis.univariate import summarize_column
from src.cleaning.data_types import convert_types, detect_column_types
from src.cleaning.duplicates import detect_duplicates, remove_duplicates
from src.cleaning.missing_values import detect_missing, fill_missing
from src.cleaning.outliers import detect_outliers_iqr, detect_outliers_zscore, handle_outliers
from src.cleaning.text_cleaning import clean_text, detect_text_issues
from src.data.loader import excel_sheet_names, load_table
from src.data.schema_detector import detect_schema
from src.quality.custom_validation import (
    evaluate_allowed_values_rule,
    evaluate_range_rule,
)
from src.quality.issue_detection import detect_issues, rank_by_importance
from src.quality.quality_score import compute_quality_score, format_quality_report
from src.quality.validation import run_all_validations
from src.reporting.export_manager import (
    export_cleaned_dataset,
    export_cleaning_log,
    export_quality_report,
)
from src.reporting.report_generator import (
    build_cleaning_report,
    build_eda_report,
    build_full_report,
    build_quality_report,
)
from src.utils.formatting import format_bytes, format_count, format_score
from src.visualization.chart_selector import (
    recommend_charts,
    recommend_correlation_chart,
    recommend_pair_chart,
)
from src.visualization.charts import (
    bar_chart,
    box_plot,
    heatmap,
    histogram,
    missingness_bar,
    quality_score_gauge,
    scatter_plot,
    line_chart,
)
from src.workspace import (
    current_data,
    current_pipeline,
    initialize_workspace,
    mark_workspace_changed,
    workspace_widget_key,
)

NAVIGATION = [
    "Dashboard",
    "Data Quality",
    "Data Cleaning",
    "Data Visualization",
    "Exploratory Data Analysis (EDA)",
    "Insights & Recommendations",
    "Reports & Export",
    "Data Source & Settings",
]
WORKFLOW_ORDER = [
    "Data Source & Settings",
    "Data Quality",
    "Data Cleaning",
    "Data Visualization",
    "Exploratory Data Analysis (EDA)",
    "Insights & Recommendations",
    "Reports & Export",
]

_PAGE_STYLE = """
<style>
    .stApp { background: #f4f7fb; }
    .block-container {
        max-width: 1600px;
        padding: 2.25rem 3rem 3rem;
    }
    h1 {
        color: #102a43;
        font-weight: 750;
        letter-spacing: -0.03em;
    }
    h2, h3 {
        color: #183a5a;
        font-weight: 700;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid #294662;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        border-radius: 10px;
        padding: 0.45rem 0.65rem;
        transition: background-color 140ms ease, outline-color 140ms ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.1);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: #24496b;
        outline: 1px solid #4b7398;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #d5dfeb;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        box-shadow: 0 2px 8px rgba(16, 42, 67, 0.05);
    }
    div[data-testid="stMetric"] label {
        color: #435b73;
        font-weight: 600;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #123e68;
        font-weight: 750;
    }
    [data-testid="stPlotlyChart"] {
        overflow: hidden;
        border: 1px solid #d5dfeb;
        border-radius: 14px;
        background: #ffffff;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #d5dfeb;
        border-radius: 10px;
    }
    .stButton button {
        min-height: 2.8rem;
        border-radius: 9px;
        font-weight: 650;
        transition: box-shadow 140ms ease, transform 140ms ease;
    }
    .stButton button:hover {
        box-shadow: 0 3px 10px rgba(20, 79, 145, 0.18);
        transform: translateY(-1px);
    }
    :focus-visible {
        outline: 3px solid #4b91d1 !important;
        outline-offset: 2px;
    }
    @media (max-width: 800px) {
        .block-container {
            padding: 1.5rem 1.25rem 2.5rem;
        }
    }
</style>
"""


def _demo_data() -> tuple[pd.DataFrame, dict[str, Any]]:
    path = Path(__file__).resolve().parents[1] / "data" / "telco_churn.csv"
    data, metadata = load_table(path.read_bytes(), path.name)
    metadata["source"] = "Bundled Telco churn demo"
    return data, metadata


def _ensure_workspace() -> None:
    if current_pipeline() is None and isinstance(st.session_state.get("data"), pd.DataFrame):
        data = st.session_state["data"]
        initialize_workspace(
            data,
            str(st.session_state.get("source", "Uploaded dataset")),
            {"rows": len(data), "columns": len(data.columns)},
        )


def _cached(name: str, factory: Callable[[], Any]) -> Any:
    cache = st.session_state.setdefault("analysis_cache", {})
    key = (int(st.session_state.get("workspace_revision", 0)), name)
    if key not in cache:
        cache[key] = factory()
    return cache[key]


def _quality_result(data: pd.DataFrame):
    return _cached("quality", lambda: compute_quality_score(data))


def _quality_issues(data: pd.DataFrame) -> list[dict[str, str]]:
    return _cached("issues", lambda: rank_by_importance(detect_issues(data)))


def _profiles(data: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return _cached("profiles", lambda: all_column_profiles(data))


def _set_workspace_page(page: str) -> None:
    st.session_state["active_workspace"] = page


def _page_shortcut(label: str, target: str, icon: str) -> None:
    st.button(
        label,
        icon=icon,
        width="stretch",
        on_click=_set_workspace_page,
        args=(target,),
    )


def _page_header(page: str) -> None:
    st.title(page)
    source = st.session_state.get("source")
    if source:
        pipeline = current_pipeline()
        approved = len(pipeline.records) if pipeline else 0
        st.caption(
            f"Shared working dataset: {source} · "
            f"{len(current_data()):,} rows × {len(current_data().columns):,} columns · "
            f"{approved} approved cleaning operation(s). "
            "The original dataset remains unchanged."
        )


def _render_workflow_navigation(page: str) -> None:
    if page not in WORKFLOW_ORDER:
        return
    index = WORKFLOW_ORDER.index(page)
    st.divider()
    st.caption(f"Analysis workflow · Step {index + 1} of {len(WORKFLOW_ORDER)}")
    with st.container(horizontal=True, horizontal_alignment="distribute"):
        if index > 0:
            previous = WORKFLOW_ORDER[index - 1]
            st.button(
                f"← Previous: {previous}",
                key="workflow_previous",
                on_click=_set_workspace_page,
                args=(previous,),
            )
        if index < len(WORKFLOW_ORDER) - 1:
            following = WORKFLOW_ORDER[index + 1]
            st.button(
                f"Next: {following} →",
                key="workflow_next",
                type="primary",
                on_click=_set_workspace_page,
                args=(following,),
            )


def _empty_data_message(data: pd.DataFrame) -> bool:
    if len(data) == 0:
        st.warning(
            "This dataset has column headers but no data rows. Load a file with "
            "records to calculate profiles, charts, or statistical summaries."
        )
        return True
    if len(data.columns) == 0:
        st.warning("This dataset has no columns. Load a dataset with a header row.")
        return True
    return False


def _show_dashboard() -> None:
    data = current_data()
    if data is None:
        st.subheader("Your workspace for trustworthy data analysis")
        st.write(
            "Start by loading your dataset. Every workspace will then use the "
            "same active working copy; approved cleaning changes remain available "
            "as you move from quality checks through analysis and reporting."
        )
        with st.container(border=True):
            st.subheader("Step 1 · Load your dataset")
            _render_upload_panel()
        with st.container(horizontal=True, horizontal_alignment="distribute"):
            if st.button(
                "Use Telco churn demo",
                key="dashboard_demo",
                icon=":material/table_view:",
            ):
                demo, metadata = _demo_data()
                initialize_workspace(demo, "Telco customer churn demo", metadata)
                st.rerun()
            st.caption("Or load the bundled sample dataset to explore the workflow.")
        return

    if _empty_data_message(data):
        _page_shortcut(
            "Open Data Source & Settings",
            "Data Source & Settings",
            ":material/upload_file:",
        )
        return

    overview = _cached("overview", lambda: dataset_overview(data))
    score = _quality_result(data)
    issues = _quality_issues(data)
    cols = st.columns(4)
    cols[0].metric("Rows", format_count(overview["n_rows"]))
    cols[1].metric("Columns", format_count(overview["n_cols"]))
    cols[2].metric("Missing cells", format_count(overview["n_missing_cells"]))
    cols[3].metric("Quality score", format_score(score.overall_score))
    cols[3].caption(score.overall_label)

    left, right = st.columns([1, 1.25], gap="large")
    with left:
        st.subheader("Quality at a glance")
        st.plotly_chart(quality_score_gauge(score.overall_score), width="stretch")
        st.caption(score.overall_interpretation)
    with right:
        st.subheader("Important issues")
        if issues:
            st.dataframe(
                pd.DataFrame(issues[:5])[
                    ["severity", "column", "title", "detail"]
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.success("No quality issues were detected by the configured checks.")

    st.subheader("Continue the analysis workflow")
    st.write(
        "These workspaces all analyze the same current working dataset. "
        "Cleaning changes are only applied after approval."
    )
    _page_shortcut(
        "Start with data quality",
        "Data Quality",
        ":material/fact_check:",
    )


def _show_quality(data: pd.DataFrame) -> None:
    if _empty_data_message(data):
        report = run_all_validations(data)
        st.dataframe(pd.DataFrame(report.to_dict()), hide_index=True, width="stretch")
        return

    st.caption(
        "A transparent weighted score based on measured completeness, validity, "
        "consistency, uniqueness, and structural quality. This is not a measure "
        "of accuracy or fitness for purpose."
    )
    score = _quality_result(data)
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.plotly_chart(quality_score_gauge(score.overall_score), width="stretch")
        st.metric("Overall score", format_score(score.overall_score))
        st.caption(score.overall_label)
        st.write(score.overall_interpretation)
        st.caption(score.overall_recommendation)
    with right:
        dimensions = format_quality_report(score)
        st.subheader("Score dimensions")
        st.dataframe(pd.DataFrame(dimensions), hide_index=True, width="stretch")
        if score.excluded_dimensions:
            st.warning(f"Not assessed: {', '.join(score.excluded_dimensions)}")

    with st.expander("Configure validation thresholds", expanded=False):
        missing_limit = st.slider(
            "Maximum missing values per column (%)",
            min_value=0,
            max_value=100,
            value=int(st.session_state.get("missing_threshold_pct", 50)),
            key="missing_threshold_pct",
        )
        duplicate_limit = st.slider(
            "Maximum duplicate rows (%)",
            min_value=0,
            max_value=100,
            value=int(st.session_state.get("duplicate_threshold_pct", 10)),
            key="duplicate_threshold_pct",
        )
    validation = run_all_validations(
        data,
        missing_threshold_pct=missing_limit,
        duplicate_threshold_pct=duplicate_limit,
    )
    st.subheader("Validation checks")
    if validation.results:
        st.dataframe(pd.DataFrame(validation.to_dict()), hide_index=True, width="stretch")
    else:
        st.info("No validation checks apply to this dataset.")

    findings = _quality_issues(data)
    st.subheader("Ranked findings")
    if findings:
        st.dataframe(pd.DataFrame(findings), hide_index=True, width="stretch")
    else:
        st.success("No quality issues detected.")

    recommendations = recommendations_for_cleaning(data, score)
    if recommendations:
        st.subheader("Recommended next steps")
        for recommendation in recommendations:
            st.write(
                f"**{recommendation['priority']} · {recommendation['dimension']}** — "
                f"{recommendation['action']}"
            )

    with st.expander("Column profiles and inferred schema"):
        st.dataframe(pd.DataFrame(_profiles(data)).T, width="stretch")
        schema = detect_schema(data)
        st.caption(
            f"{schema['n_identifier_candidates']} identifier candidate(s), "
            f"{schema['n_empty_columns']} empty column(s), "
            f"{schema['n_constant_columns']} constant column(s)."
        )


def _preview_operation(
    operation: str,
    candidate: pd.DataFrame,
    records: list[Any],
) -> None:
    st.session_state["cleaning_preview"] = {
        "workspace_id": st.session_state.get("workspace_id"),
        "revision": int(st.session_state.get("workspace_revision", 0)),
        "operation": operation,
        "data": candidate.copy(deep=True),
        "records": records,
    }


def _preview_candidates(data: pd.DataFrame, operation: str, values: dict[str, Any]):
    if operation == "Remove duplicates":
        return remove_duplicates(
            data,
            subset=values["subset"] or None,
            keep=values["keep"],
        )
    if operation == "Handle missing values":
        return fill_missing(
            data,
            {values["column"]: (values["method"], values["custom"])},
        )
    if operation == "Convert column type":
        return convert_types(data, {values["column"]: values["target"]})
    if operation == "Normalize text and categories":
        return clean_text(
            data,
            {
                values["column"]: {
                    "trim": values["trim"],
                    "collapse_spaces": values["collapse"],
                    "case": values["case"],
                    "standardize": values["mapping"],
                }
            },
        )
    if operation == "Investigate outliers":
        return handle_outliers(
            data,
            {
                values["column"]: {
                    "method": values["method"],
                    "action": values["action"],
                    "multiplier": values["threshold"],
                    "threshold": values["threshold"],
                }
            },
        )
    raise ValueError(f"Unsupported cleaning operation: {operation}")


def _show_cleaning_preview(data: pd.DataFrame) -> None:
    preview = st.session_state.get("cleaning_preview")
    if not preview:
        return
    is_current = (
        preview["workspace_id"] == st.session_state.get("workspace_id")
        and preview["revision"] == int(st.session_state.get("workspace_revision", 0))
    )
    if not is_current:
        st.warning("This preview is stale because the dataset changed. Create a new preview.")
        st.session_state.pop("cleaning_preview", None)
        return

    candidate = preview["data"]
    st.subheader(f"Preview · {preview['operation']}")
    before_after = pd.DataFrame(
        [
            {
                "Version": "Current",
                "Rows": len(data),
                "Columns": len(data.columns),
                "Missing cells": int(data.isna().sum().sum()),
            },
            {
                "Version": "Proposed",
                "Rows": len(candidate),
                "Columns": len(candidate.columns),
                "Missing cells": int(candidate.isna().sum().sum()),
            },
        ]
    )
    st.dataframe(before_after, hide_index=True, width="stretch")
    st.dataframe(candidate.head(20), width="stretch")
    records = preview["records"]
    if records:
        st.dataframe(
            pd.DataFrame(
                [record.to_dict() if hasattr(record, "to_dict") else record for record in records]
            ),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("The operation made no changes.")

    with st.container(horizontal=True):
        can_apply = any(getattr(record, "succeeded", True) for record in records)
        if st.button(
            "Approve and apply",
            key="approve_cleaning_preview",
            type="primary",
            disabled=not can_apply,
        ):
            pipeline = current_pipeline()
            if pipeline is None:
                st.error("No active workspace. Reload the dataset before applying this change.")
                return
            pipeline.apply_preview(candidate, records)
            mark_workspace_changed()
            st.success("Approved change applied. Derived analyses have been refreshed.")
            st.rerun()
        if st.button("Reject preview", key="reject_cleaning_preview"):
            st.session_state.pop("cleaning_preview", None)
            st.rerun()


def _show_validation_rules(data: pd.DataFrame) -> None:
    st.subheader("Custom validation rules")
    columns = data.columns.tolist()
    numeric_columns = data.select_dtypes(include="number").columns.tolist()
    with st.form("add_custom_validation_rule"):
        kind = st.selectbox("Rule type", ["Numeric range", "Allowed values"])
        candidates = numeric_columns if kind == "Numeric range" else columns
        if not candidates:
            st.info("No compatible columns are available for this rule.")
            submitted = st.form_submit_button("Add validation rule", disabled=True)
            column = ""
            lower = upper = allowed = ""
        else:
            column = st.selectbox("Column", candidates)
            if kind == "Numeric range":
                lower = st.text_input("Minimum (optional)")
                upper = st.text_input("Maximum (optional)")
                allowed = ""
            else:
                allowed = st.text_input("Allowed values (comma-separated)")
                lower = upper = ""
            submitted = st.form_submit_button("Add validation rule")

    if submitted:
        try:
            if kind == "Numeric range":
                minimum = float(lower) if lower.strip() else None
                maximum = float(upper) if upper.strip() else None
                evaluate_range_rule(data, column, minimum, maximum)
                rule = {
                    "type": "range",
                    "column": column,
                    "minimum": minimum,
                    "maximum": maximum,
                }
            else:
                allowed_values = [value.strip() for value in allowed.split(",") if value.strip()]
                evaluate_allowed_values_rule(data, column, allowed_values)
                rule = {
                    "type": "allowed_values",
                    "column": column,
                    "values": allowed_values,
                }
            st.session_state.setdefault("custom_validation_rules", []).append(rule)
            st.rerun()
        except ValueError as error:
            st.error(str(error))

    rules = st.session_state.get("custom_validation_rules", [])
    if not rules:
        st.caption("No custom rules configured.")
        return
    results = []
    for rule in rules:
        try:
            if rule["type"] == "range":
                result = evaluate_range_rule(
                    data, rule["column"], rule["minimum"], rule["maximum"]
                )
                description = (
                    f"{rule['minimum'] if rule['minimum'] is not None else '−∞'} to "
                    f"{rule['maximum'] if rule['maximum'] is not None else '∞'}"
                )
            else:
                result = evaluate_allowed_values_rule(
                    data, rule["column"], rule["values"]
                )
                description = ", ".join(rule["values"])
            results.append(
                {
                    "Column": rule["column"],
                    "Rule": rule["type"],
                    "Criteria": description,
                    "Checked": result["checked"],
                    "Violations": result["invalid"],
                }
            )
        except ValueError as error:
            st.warning(f"Stored rule is not currently applicable: {error}")
    if results:
        st.dataframe(pd.DataFrame(results), hide_index=True, width="stretch")
    if st.button("Clear custom validation rules", key="clear_validation_rules"):
        st.session_state["custom_validation_rules"] = []
        st.rerun()


def _show_cleaning(data: pd.DataFrame) -> None:
    if _empty_data_message(data):
        return
    pipeline = current_pipeline()
    if pipeline is None:
        st.error("The cleaning workspace is unavailable. Reload the data source.")
        return

    st.caption(
        "Every transformation is previewed before approval. The original dataset "
        "is kept separately from this working copy."
    )
    metrics = st.columns(3)
    metrics[0].metric("Original rows", format_count(len(pipeline.source)))
    metrics[1].metric("Working rows", format_count(len(data)))
    metrics[2].metric("Approved operations", format_count(len(pipeline.records)))

    operation = st.selectbox(
        "Choose a cleaning operation",
        [
            "Remove duplicates",
            "Handle missing values",
            "Convert column type",
            "Normalize text and categories",
            "Investigate outliers",
        ],
        key=workspace_widget_key("clean_operation"),
    )
    all_columns = data.columns.tolist()
    values: dict[str, Any] = {}
    operation_available = True
    with st.form("cleaning_operation_form"):
        if operation == "Remove duplicates":
            duplicate_report = detect_duplicates(data)
            st.write(
                f"{duplicate_report['n_duplicate_rows']:,} rows participate in "
                f"exact duplicates ({duplicate_report['duplicate_pct']}%)."
            )
            values["subset"] = st.multiselect(
                "Columns to compare (none means all columns)",
                all_columns,
                key=workspace_widget_key("duplicate_subset"),
            )
            values["keep"] = st.selectbox("Keep occurrence", ["first", "last"])
        elif operation == "Handle missing values":
            missing = detect_missing(data)
            candidates = [column for column, report in missing.items() if report["n_missing"]]
            if not candidates:
                st.info("No missing values or configured placeholders were detected.")
                operation_available = False
            else:
                values["column"] = st.selectbox("Column", candidates)
                methods = ["Drop rows", "Mode", "Custom"]
                if pd.api.types.is_numeric_dtype(data[values["column"]]):
                    methods[1:1] = ["Mean", "Median"]
                values["method"] = st.selectbox("Strategy", methods)
                values["custom"] = (
                    st.text_input("Custom replacement")
                    if values["method"] == "Custom"
                    else ""
                )
        elif operation == "Convert column type":
            values["column"] = st.selectbox("Column", all_columns)
            values["target"] = st.selectbox(
                "Convert to",
                ["numeric", "integer", "datetime", "categorical", "string", "boolean"],
            )
            inferred = detect_column_types(data)[values["column"]]
            st.caption(
                f"Detected: {inferred['inferred_type']} "
                f"(confidence {inferred['confidence']})"
            )
        elif operation == "Normalize text and categories":
            text_columns = data.select_dtypes(include=["object", "string", "category"]).columns.tolist()
            if not text_columns:
                st.info("No text or categorical columns are available.")
                operation_available = False
            else:
                detected_issues = detect_text_issues(data)
                values["column"] = st.selectbox("Column", text_columns)
                issues = detected_issues.get(values["column"], {}).get("issues", [])
                st.caption(
                    "; ".join(issues) if issues else "No common text-quality issues detected."
                )
                values["trim"] = st.checkbox("Trim surrounding whitespace", value=True)
                values["collapse"] = st.checkbox("Collapse repeated spaces", value=True)
                values["case"] = st.selectbox("Normalize case", ["none", "lower", "upper", "title"])
                mapping_text = st.text_area(
                    "Category standardization map (JSON object)",
                    value="{}",
                    help='Example: {"NY": "New York", "N.Y.": "New York"}',
                )
        else:
            numeric_columns = data.select_dtypes(include="number").columns.tolist()
            if not numeric_columns:
                st.info("No numeric columns are available for outlier analysis.")
                operation_available = False
            else:
                values["column"] = st.selectbox("Numeric column", numeric_columns)
                values["method"] = st.selectbox("Detection method", ["iqr", "zscore"])
                values["threshold"] = st.number_input(
                    "IQR multiplier or absolute Z-score threshold",
                    min_value=0.1,
                    max_value=10.0,
                    value=1.5 if values["method"] == "iqr" else 3.0,
                    step=0.1,
                )
                values["action"] = st.selectbox("Action", ["cap", "remove", "flag"])

        submitted = st.form_submit_button(
            "Build transformation preview",
            type="primary",
            disabled=not operation_available,
        )

    if submitted:
        try:
            if operation in {"Handle missing values", "Normalize text and categories", "Investigate outliers"} and not values:
                st.info("This operation has no compatible columns in the current dataset.")
                return
            if operation == "Investigate outliers":
                result = (
                    detect_outliers_iqr(data, values["column"], values["threshold"])
                    if values["method"] == "iqr"
                    else detect_outliers_zscore(data, values["column"], values["threshold"])
                )
                st.write(
                    f"Detected **{result['n_outliers']:,}** outlier(s) using "
                    f"{values['method'].upper()}."
                )
                if not result["n_outliers"]:
                    st.info("There are no flagged observations to transform.")
                    st.session_state.pop("cleaning_preview", None)
                    return
            if operation == "Normalize text and categories":
                mapping = json.loads(mapping_text)
                if not isinstance(mapping, dict) or not all(
                    isinstance(key, str) and isinstance(value, str)
                    for key, value in mapping.items()
                ):
                    raise ValueError("The standardization map must be a JSON object of strings.")
                values["mapping"] = mapping
            candidate, records = _preview_candidates(data, operation, values)
            _preview_operation(operation, candidate, records)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            st.error(f"Could not build this preview: {error}")

    _show_cleaning_preview(data)
    st.divider()
    _show_validation_rules(data)
    st.divider()

    st.subheader("Approved cleaning history")
    if pipeline.records:
        st.dataframe(
            pd.DataFrame([record.to_dict() for record in pipeline.records]),
            hide_index=True,
            width="stretch",
        )
        controls = st.columns(2)
        if controls[0].button("Undo last approved operation", disabled=not pipeline.can_undo):
            pipeline.undo()
            mark_workspace_changed()
            st.rerun()
        if controls[1].button("Reset working copy to original"):
            pipeline.reset()
            mark_workspace_changed()
            st.rerun()
    else:
        st.info("No approved transformations yet.")

    st.subheader("Working dataset preview")
    st.dataframe(data.head(20), width="stretch")


def _filter_data(data: pd.DataFrame, key_prefix: str) -> pd.DataFrame:
    filter_column = st.selectbox(
        "Filter column",
        ["No filter", *data.columns.tolist()],
        key=workspace_widget_key(f"{key_prefix}_filter_column"),
    )
    if filter_column == "No filter":
        return data
    series = data[filter_column]
    if pd.api.types.is_numeric_dtype(series):
        numeric = series.dropna()
        if numeric.empty or numeric.min() == numeric.max():
            st.caption("This column has no numeric range to filter.")
            return data
        low, high = st.slider(
            "Keep values in range",
            min_value=float(numeric.min()),
            max_value=float(numeric.max()),
            value=(float(numeric.min()), float(numeric.max())),
            key=workspace_widget_key(f"{key_prefix}_filter_range"),
        )
        return data.loc[series.between(low, high) | series.isna()]

    options = series.dropna().unique().tolist()
    selected = st.multiselect(
        "Keep categories",
        options,
        default=options,
        key=workspace_widget_key(f"{key_prefix}_filter_values"),
    )
    return data.loc[series.isna() | series.isin(selected)]


def _draw_recommended_chart(
    data: pd.DataFrame,
    chart_type: str,
    x: str,
    y: str | None,
    color: str | None,
):
    if chart_type == "histogram":
        return histogram(data, x, color_column=color)
    if chart_type == "box_plot":
        if y is None:
            return box_plot(data, x)
        return box_plot(data, y, category_column=x)
    if chart_type == "bar_chart":
        if y is None:
            return bar_chart(data, x)
        if pd.api.types.is_numeric_dtype(data[y]):
            grouped = data.groupby(x, dropna=False)[y].mean().reset_index()
            return px.bar(grouped, x=x, y=y, color=color, title=f"Mean {y} by {x}")
        counts = data.groupby([x, y], dropna=False).size().reset_index(name="Count")
        return px.bar(
            counts,
            x=x,
            y="Count",
            color=y if color is None else color,
            barmode="group",
            title=f"{y} counts by {x}",
        )
    if chart_type == "scatter_plot" and y is not None:
        return scatter_plot(data, x, y, color_column=color)
    if chart_type == "line_chart" and y is not None:
        if not pd.api.types.is_numeric_dtype(data[y]):
            dates = pd.to_datetime(data[x], errors="coerce", format="mixed")
            plot_data = data.assign(_date=dates).dropna(subset=["_date", y])
            counts = (
                plot_data.groupby(["_date", y], dropna=False)
                .size()
                .reset_index(name="Count")
            )
            return px.line(
                counts,
                x="_date",
                y="Count",
                color=color or y,
                title=f"{y} counts over {x}",
            )
        return line_chart(data, x, y, color_column=color)
    return None


def _show_visualization(data: pd.DataFrame) -> None:
    if _empty_data_message(data):
        return
    filtered = _filter_data(data, "chart")
    if filtered.empty:
        st.info("No rows match the selected filter.")
        return

    left, right = st.columns(2)
    with left:
        x = st.selectbox(
            "X / analysis column",
            filtered.columns,
            key=workspace_widget_key("chart_x"),
        )
    with right:
        y_options = ["No second column", *[c for c in filtered.columns if c != x]]
        y_key = workspace_widget_key("chart_y")
        selected_y = st.session_state.get(y_key)
        default_y = y_options.index(selected_y) if selected_y in y_options else 0
        y_choice = st.selectbox("Y / comparison column", y_options, index=default_y, key=y_key)
    y = None if y_choice == "No second column" else y_choice

    if y:
        recommendations = recommend_pair_chart(filtered, x, y)
    else:
        recommendations = recommend_charts(filtered, [x]).get(x, [])
    chart_types = list(dict.fromkeys(item["chart_type"] for item in recommendations))
    if not chart_types:
        st.info("No compatible chart is available for this column selection.")
        return

    chart_type_key = workspace_widget_key("chart_type")
    previous_chart = st.session_state.get(chart_type_key)
    chart_type = st.selectbox(
        "Recommended chart",
        chart_types,
        index=chart_types.index(previous_chart) if previous_chart in chart_types else 0,
        format_func=lambda value: value.replace("_", " ").title(),
        key=chart_type_key,
    )
    color_options = [
        column for column in filtered.columns
        if column not in {x, y} and not pd.api.types.is_numeric_dtype(filtered[column])
    ]
    color_options = ["None", *color_options]
    color_choice = st.selectbox(
        "Group / color by",
        color_options,
        key=workspace_widget_key("chart_color"),
    )
    color = None if color_choice == "None" else color_choice
    figure = _draw_recommended_chart(filtered, chart_type, x, y, color)
    if figure is None:
        st.info("This chart requires a second column. Select an X/Y pair.")
        return
    st.plotly_chart(figure, width="stretch")
    st.caption(
        next(
            (item["reason"] for item in recommendations if item["chart_type"] == chart_type),
            "Chart recommended from the selected variable types.",
        )
    )
    st.download_button(
        "Download interactive chart (HTML)",
        figure.to_html(include_plotlyjs="cdn").encode("utf-8"),
        file_name=f"{chart_type}_{x}.html",
        mime="text/html",
        key="download_chart_html",
    )
    st.download_button(
        "Download filtered chart data (CSV)",
        filtered.to_csv(index=False).encode("utf-8"),
        file_name="chart_data.csv",
        mime="text/csv",
        key="download_chart_data",
    )


def _show_eda(data: pd.DataFrame) -> None:
    if _empty_data_message(data):
        return
    overview = _cached("overview", lambda: dataset_overview(data))
    metrics = st.columns(4)
    metrics[0].metric("Rows", format_count(overview["n_rows"]))
    metrics[1].metric("Columns", format_count(overview["n_cols"]))
    metrics[2].metric("Missing cells", format_count(overview["n_missing_cells"]))
    metrics[3].metric("Duplicate rows", format_count(overview["n_duplicates"]))
    st.plotly_chart(missingness_bar(data), width="stretch")

    profiles = _profiles(data)
    st.subheader("Univariate and descriptive analysis")
    selected = st.selectbox(
        "Choose a variable",
        ["Choose a column", *data.columns.tolist()],
        key=workspace_widget_key("eda_univariate_column"),
    )
    if selected != "Choose a column":
        profile = profiles.get(selected) or column_profile(data[selected])
        st.write(
            f"**Inferred type:** {profile['dtype']} · "
            f"**Missing:** {profile['n_missing']:,} ({profile['missing_pct']}%) · "
            f"**Unique:** {profile['n_unique']:,}"
        )
        summary = summarize_column(data[selected])
        st.json(summary)
        recommendations = recommend_charts(data, [selected]).get(selected, [])
        chart_type = next((item["chart_type"] for item in recommendations), None)
        figure = _draw_recommended_chart(data, chart_type, selected, None, None) if chart_type else None
        if figure is not None:
            st.plotly_chart(figure, width="stretch")
        else:
            st.caption("No distribution chart is available for this variable type.")

    st.subheader("Bivariate analysis")
    if len(data.columns) < 2:
        st.info("Bivariate analysis requires at least two columns.")
    else:
        col_a = st.selectbox(
            "First variable",
            data.columns,
            key=workspace_widget_key("eda_pair_a"),
        )
        col_b_options = [column for column in data.columns if column != col_a]
        col_b_key = workspace_widget_key("eda_pair_b")
        previous = st.session_state.get(col_b_key)
        col_b = st.selectbox(
            "Second variable",
            col_b_options,
            index=col_b_options.index(previous) if previous in col_b_options else 0,
            key=col_b_key,
        )
        pair = analyze_pair(data, col_a, col_b)
        st.write(f"**Method:** {pair.get('recommendation', 'Pairwise descriptive summary')}")
        if "groups" in pair:
            st.dataframe(pd.DataFrame(pair["groups"]).T, width="stretch")
        elif "contingency" in pair:
            st.dataframe(pd.DataFrame(pair["contingency"]).fillna(0), width="stretch")
            if pair.get("cramers_v") is not None:
                st.metric("Cramér's V", pair["cramers_v"])
        elif "correlation" in pair:
            st.json(pair)
        else:
            st.json(pair)
        chart_recommendations = recommend_pair_chart(data, col_a, col_b)
        for recommendation in chart_recommendations:
            figure = _draw_recommended_chart(
                data,
                recommendation["chart_type"],
                recommendation.get("x", col_a),
                recommendation.get("y", col_b),
                recommendation.get("category_column"),
            )
            if figure is not None:
                st.plotly_chart(figure, width="stretch")

    st.subheader("Correlation analysis")
    correlation_recommendation = recommend_correlation_chart(data)
    if not correlation_recommendation["recommended"]:
        st.info(correlation_recommendation["reason"])
    else:
        method = st.selectbox(
            "Correlation method",
            ["pearson", "spearman"],
            key=workspace_widget_key("eda_correlation_method"),
        )
        result = pairwise_correlations(data, method=method)
        matrix = pd.DataFrame(result["coefficients"])
        st.plotly_chart(
            heatmap(matrix, title=f"{method.title()} correlation matrix"),
            width="stretch",
        )
        with st.expander("Correlation sample sizes and limitations"):
            st.dataframe(pd.DataFrame(result["sample_sizes"]), width="stretch")
            for warning in result["warnings"]:
                st.write(f"- {warning}")

    st.subheader("Grouped analysis")
    category_columns = data.select_dtypes(
        include=["object", "string", "category", "bool"]
    ).columns.tolist()
    numeric_columns = data.select_dtypes(include="number").columns.tolist()
    if category_columns and numeric_columns:
        group_col = st.selectbox(
            "Group by",
            category_columns,
            key=workspace_widget_key("eda_group_column"),
        )
        value_col = st.selectbox(
            "Summarize numeric variable",
            numeric_columns,
            key=workspace_widget_key("eda_group_value"),
        )
        grouped = data.groupby(group_col, dropna=False)[value_col].agg(
            ["count", "mean", "median", "std", "min", "max"]
        )
        st.dataframe(grouped, width="stretch")
        st.caption("Groups with missing values are retained; summary statistics ignore null targets.")
    else:
        st.info("Grouped numeric summaries require at least one categorical and one numeric column.")


def _show_insights(data: pd.DataFrame) -> None:
    if _empty_data_message(data):
        return
    insights = _cached(
        "insights",
        lambda: generate_insights(data, _quality_result(data)),
    )
    if not insights:
        st.info("No evidence-backed findings are available for this dataset.")
        return
    for insight in insights:
        with st.container(border=True):
            st.markdown(f"### {insight['title']}")
            st.caption(insight["category"])
            st.write(insight["observation"])
            st.write(f"**Evidence:** {insight['evidence']}")
            st.write(f"**Why it matters:** {insight['why_it_matters']}")
            st.write(f"**Recommended action:** {insight['recommended_action']}")
            st.caption(f"Limitation: {insight['limitation']}")


def _show_reports(data: pd.DataFrame) -> None:
    if _empty_data_message(data):
        return
    original = st.session_state["original_data"]
    pipeline = current_pipeline()
    records = [record.to_dict() for record in pipeline.records] if pipeline else []
    score = _quality_result(data)

    st.subheader("Dataset downloads")
    left, right = st.columns(2)
    with left:
        csv_data, csv_name, csv_mime = export_cleaned_dataset(data, "csv")
        st.download_button(
            "Download cleaned dataset (CSV)",
            csv_data,
            csv_name,
            csv_mime,
            key="report_clean_csv",
        )
    with right:
        excel_data, excel_name, excel_mime = export_cleaned_dataset(data, "excel")
        st.download_button(
            "Download cleaned dataset (Excel)",
            excel_data,
            excel_name,
            excel_mime,
            key="report_clean_excel",
        )

    st.subheader("Analysis and audit reports")
    quality_report = build_quality_report(data, score)
    eda_report = build_eda_report(data)
    cleaning_report = build_cleaning_report(original, data, records)
    full_report = build_full_report(original, data, records, score)
    report_buttons = st.columns(3)
    report_buttons[0].download_button(
        "Download quality report (CSV)",
        export_quality_report(format_quality_report(score))[0],
        "quality_report.csv",
        "text/csv",
    )
    report_buttons[1].download_button(
        "Download EDA report (JSON)",
        json.dumps(eda_report, indent=2, default=str).encode("utf-8"),
        "eda_report.json",
        "application/json",
    )
    report_buttons[2].download_button(
        "Download full analysis (JSON)",
        json.dumps(full_report, indent=2, default=str).encode("utf-8"),
        "datalens_report.json",
        "application/json",
    )
    log_data, log_name, log_mime = export_cleaning_log(records)
    st.download_button(
        "Download cleaning audit log (CSV)",
        log_data,
        log_name,
        log_mime,
        key="report_cleaning_log",
    )

    st.subheader("Before and after")
    before_score = compute_quality_score(original)
    comparison = pd.DataFrame(
        [
            {
                "Version": "Original",
                "Rows": len(original),
                "Columns": len(original.columns),
                "Missing cells": int(original.isna().sum().sum()),
                "Quality score": before_score.overall_score,
            },
            {
                "Version": "Current working copy",
                "Rows": len(data),
                "Columns": len(data.columns),
                "Missing cells": int(data.isna().sum().sum()),
                "Quality score": score.overall_score,
            },
        ]
    )
    st.dataframe(comparison, hide_index=True, width="stretch")
    st.caption(
        f"Report includes {quality_report['n_findings']} ranked quality finding(s) "
        f"and {cleaning_report['n_operations']} approved cleaning operation(s)."
    )


def _upload_signature(
    filename: str,
    delimiter: str,
    encoding: str,
    sheet_name: str | int,
) -> tuple[str, str, str, str]:
    return (filename, delimiter, encoding, str(sheet_name))


def _reset_workspace() -> None:
    for key in (
        "data",
        "original_data",
        "cleaned_data",
        "cleaning_pipeline",
        "cleaning_log",
        "source",
        "dataset_metadata",
        "workspace_id",
        "workspace_revision",
        "analysis_cache",
        "cleaning_preview",
        "workspace_after_upload",
        "custom_validation_rules",
        "upload_candidate",
        "upload_candidate_metadata",
        "upload_candidate_signature",
    ):
        st.session_state.pop(key, None)


def _render_upload_panel() -> None:
    st.write(
        "Upload a CSV or Excel workbook, preview the parsed table, and confirm "
        "before it becomes the active dataset."
    )
    uploaded = st.file_uploader(
        "Choose a CSV or Excel workbook",
        type=["csv", "xlsx", "xlsm"],
        key="source_file",
    )
    if uploaded is not None:
        extension = Path(uploaded.name).suffix.casefold()
        delimiter_label = st.selectbox(
            "CSV delimiter",
            ["Auto-detect", "Comma", "Semicolon", "Tab", "Pipe"],
            disabled=extension != ".csv",
        )
        delimiter_map = {
            "Auto-detect": "auto",
            "Comma": ",",
            "Semicolon": ";",
            "Tab": "\t",
            "Pipe": "|",
        }
        encoding_label = st.selectbox(
            "CSV encoding",
            ["Auto-detect", "UTF-8", "Windows-1252", "Latin-1"],
            disabled=extension != ".csv",
        )
        encoding_map = {
            "Auto-detect": "auto",
            "UTF-8": "utf-8",
            "Windows-1252": "cp1252",
            "Latin-1": "latin-1",
        }
        sheet_name: str | int = 0
        if extension in {".xlsx", ".xlsm"}:
            try:
                sheets = excel_sheet_names(uploaded.getvalue())
                if not sheets:
                    st.error("This workbook does not contain any worksheets.")
                    return
                sheet_name = st.selectbox("Worksheet", sheets, key="source_excel_sheet")
            except ValueError as error:
                st.error(str(error))
                return

        delimiter = delimiter_map[delimiter_label]
        encoding = encoding_map[encoding_label]
        signature = _upload_signature(uploaded.name, delimiter, encoding, sheet_name)
        if st.session_state.get("upload_candidate_signature") != signature:
            st.session_state.pop("upload_candidate", None)
            st.session_state.pop("upload_candidate_metadata", None)

        if st.button("Preview selected file", type="primary", key="preview_source_file"):
            try:
                with st.spinner("Validating and reading the selected file…"):
                    data, metadata = load_table(
                        uploaded.getvalue(),
                        uploaded.name,
                        delimiter=delimiter,
                        encoding=encoding,
                        sheet_name=sheet_name,
                    )
                st.session_state["upload_candidate"] = data
                st.session_state["upload_candidate_metadata"] = metadata
                st.session_state["upload_candidate_signature"] = signature
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except OSError as error:
                st.error(f"Could not read the selected file: {error}")

        candidate = st.session_state.get("upload_candidate")
        if (
            isinstance(candidate, pd.DataFrame)
            and st.session_state.get("upload_candidate_signature") == signature
        ):
            metadata = st.session_state["upload_candidate_metadata"]
            st.subheader("Validated file preview")
            metrics = st.columns(4)
            metrics[0].metric("File size", format_bytes(metadata["file_size_bytes"]))
            metrics[1].metric("Rows", format_count(metadata["rows"]))
            metrics[2].metric("Columns", format_count(metadata["columns"]))
            metrics[3].metric("Format", metadata["format"])
            if metadata.get("delimiter"):
                st.caption(
                    f"Detected delimiter: {metadata['delimiter']!r} · "
                    f"Encoding: {metadata['encoding']}"
                )
            if metadata.get("sheet_name"):
                st.caption(f"Worksheet: {metadata['sheet_name']}")
            st.dataframe(candidate.head(25), width="stretch")
            confirm_label = (
                "Confirm and replace active dataset"
                if current_data() is not None
                else "Confirm and load dataset"
            )
            if st.button(
                confirm_label,
                key="confirm_dataset_replacement",
                type="primary",
            ):
                initialize_workspace(candidate, uploaded.name, metadata)
                st.session_state.pop("custom_validation_rules", None)
                st.session_state.pop("upload_candidate", None)
                st.session_state.pop("upload_candidate_metadata", None)
                st.session_state.pop("upload_candidate_signature", None)
                active_page = st.session_state.get("active_workspace", "Dashboard")
                st.session_state["workspace_after_upload"] = (
                    active_page
                    if active_page not in {"Dashboard", "Data Source & Settings"}
                    else "Dashboard"
                )
                st.success(
                    "Dataset loaded. All workspaces now use this dataset; "
                    "the original is preserved as the source copy."
                )
                st.rerun()


def _show_data_source() -> None:
    st.write(
        "Files are parsed and held in memory for this session. Replacing the "
        "active dataset requires preview and confirmation; this starts a fresh "
        "analysis workspace."
    )
    _render_upload_panel()

    st.divider()
    if current_data() is not None:
        data = current_data()
        metadata = st.session_state.get("dataset_metadata", {})
        st.subheader("Active dataset")
        st.write(f"**Source:** {st.session_state.get('source', 'Unknown')}")
        st.write(
            f"**Shape:** {len(data):,} rows × {len(data.columns):,} columns · "
            f"**Memory:** {format_bytes(int(data.memory_usage(deep=True).sum()))}"
        )
        st.dataframe(data.head(10), width="stretch")
        if metadata:
            with st.expander("Source metadata"):
                st.json(metadata)
    else:
        st.info("No active dataset. Load a file above or use the demo from Dashboard.")

    st.subheader("Workspace controls")
    confirmation = st.checkbox(
        "I understand this clears the active dataset and approved cleaning history.",
        key="confirm_workspace_reset",
    )
    if st.button("Reset workspace", disabled=not confirmation, key="reset_workspace"):
        _reset_workspace()
        st.success("Workspace reset. Load a dataset to begin again.")
        st.rerun()


def run_app() -> None:
    """Render the persistent navigation shell and one dedicated workspace."""
    st.markdown(_PAGE_STYLE, unsafe_allow_html=True)
    _ensure_workspace()
    requested_page = st.session_state.pop("workspace_after_upload", None)
    if requested_page in NAVIGATION:
        st.session_state["active_workspace"] = requested_page
    with st.sidebar:
        st.title("DataFlow Analytics")
        st.caption("Data quality · cleaning · analysis")
        selected_page = st.radio(
            "Workspace",
            NAVIGATION,
            key="active_workspace",
            label_visibility="collapsed",
        )
        data = current_data()
        st.divider()
        if data is not None:
            st.caption(f"Active dataset: {st.session_state.get('source', 'Unknown')}")
            st.caption(f"{len(data):,} rows · {len(data.columns):,} columns")
        elif isinstance(st.session_state.get("upload_candidate"), pd.DataFrame):
            st.caption("Upload preview ready · confirm it to activate the dataset")
        else:
            st.caption("No dataset loaded")

    _page_header(selected_page)
    data = current_data()
    if selected_page == "Dashboard":
        _show_dashboard()
        return
    if selected_page == "Data Source & Settings":
        _show_data_source()
        _render_workflow_navigation(selected_page)
        return
    if data is None:
        st.info(
            "Load a dataset first. This workspace will automatically use the "
            "same active dataset after you confirm the upload."
        )
        with st.container(border=True):
            st.subheader("Load your dataset to continue")
            _render_upload_panel()
        return

    renderers: dict[str, Callable[[pd.DataFrame], None]] = {
        "Data Quality": _show_quality,
        "Data Cleaning": _show_cleaning,
        "Data Visualization": _show_visualization,
        "Exploratory Data Analysis (EDA)": _show_eda,
        "Insights & Recommendations": _show_insights,
        "Reports & Export": _show_reports,
    }
    renderers[selected_page](data)
    _render_workflow_navigation(selected_page)
