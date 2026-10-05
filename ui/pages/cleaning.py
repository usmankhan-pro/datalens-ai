"""Data Cleaning page — cleaning operations workspace."""

import pandas as pd
import streamlit as st

from core.cleaning import apply_operation, export_history_script, preview_operation
from core.utils.state import DatasetBundle, FileMeta, TransformRecord, get_bundle, has_dataset, set_bundle


def _render_operation_controls(df: pd.DataFrame) -> None:
    """Render simple operation controls for preview/apply workflows."""
    op = st.selectbox("Operation", ["remove_duplicates", "fill_missing_numeric", "standardize_text"])
    if op == "fill_missing_numeric":
        method = st.selectbox("Method", ["mean", "median", "mode"])
        params = {"method": method}
    elif op == "standardize_text":
        case = st.selectbox("Case", ["upper", "lower", "title"])
        params = {"case": case, "strip": True}
    else:
        params = {}

    preview = preview_operation(df, op, params)
    st.subheader("Preview")
    st.write(f"Rows affected: {preview['rows_affected']}")
    st.dataframe(preview["preview"], use_container_width=True)

    if st.button("Apply Changes"):
        result = apply_operation(df, op, params)
        bundle = get_bundle()
        if bundle is not None:
            bundle.working_df = result["df"].copy()
            bundle.transformation_history.append(
                TransformRecord(
                    timestamp=str(pd.Timestamp.now()),
                    operation=op,
                    columns=list(result["df"].columns),
                    params=params,
                    rows_affected=result["rows_affected"],
                )
            )
            set_bundle(bundle)
            st.success("Cleaning operation applied.")
            st.rerun()

    if st.button("Reset Changes"):
        bundle = get_bundle()
        if bundle is not None:
            bundle.working_df = bundle.original_df.copy()
            bundle.transformation_history = []
            set_bundle(bundle)
            st.success("Working dataset reset to the original data.")
            st.rerun()

    if bundle := get_bundle():
        history = bundle.transformation_history
        if history:
            st.subheader("Cleaning History")
            st.dataframe(pd.DataFrame([
                {
                    "timestamp": item.timestamp,
                    "operation": item.operation,
                    "rows_affected": item.rows_affected,
                    "params": str(item.params),
                }
                for item in history
            ]), use_container_width=True)
            script = export_history_script(history)
            st.code(script, language="python")


def page() -> None:
    """Render the Data Cleaning page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🧹 Data Cleaning")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🧹</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to access the cleaning workspace.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for cleaning.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.subheader("Working Dataset")
    st.dataframe(bundle.working_df.head(100), use_container_width=True)
    _render_operation_controls(bundle.working_df)

    st.markdown("</div>", unsafe_allow_html=True)
