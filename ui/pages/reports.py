"""Export & Reports page — Before/after comparison and dataset exports."""

import html
import streamlit as st
import pandas as pd

from core.export.comparator import compare_datasets
from core.export.script_generator import generate_cleaning_script
from core.reporting import (
    generate_csv_report,
    generate_excel_report,
    generate_json_export,
    generate_cleaning_log_export,
    generate_pdf_report,
)
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Export & Reports page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📦 Export & Reports")
    st.caption("Review before/after cleaning metrics, download cleaned data, reports, and reproducible scripts.")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📦</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to access export options and reports.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for export.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    orig_df = bundle.original_df
    work_df = bundle.working_df
    history = getattr(bundle, "transformation_history", [])
    quality_summary = getattr(bundle, "quality_result", None) or {"overall_score": 100.0}
    issues = quality_summary.get("issues", []) if isinstance(quality_summary, dict) else []

    # 1. Before vs. After Comparison
    st.subheader("📊 Before vs. After Cleaning Comparison")
    comparison = compare_datasets(orig_df, work_df)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            label="Total Rows",
            value=f"{comparison.after_rows:,}",
            delta=f"{comparison.rows_diff:+d}" if comparison.rows_diff != 0 else None,
        )
    with col2:
        st.metric(
            label="Total Columns",
            value=f"{comparison.after_cols}",
            delta=f"{comparison.cols_diff:+d}" if comparison.cols_diff != 0 else None,
        )
    with col3:
        st.metric(
            label="Missing Values",
            value=f"{comparison.after_missing_pct:.1f}%",
            delta=f"{comparison.missing_pct_diff:+.1f}%" if comparison.missing_pct_diff != 0 else None,
            delta_color="inverse",
        )
    with col4:
        st.metric(
            label="Duplicates",
            value=f"{comparison.after_duplicates:,}",
            delta=f"{comparison.duplicates_diff:+d}" if comparison.duplicates_diff != 0 else None,
            delta_color="inverse",
        )
    with col5:
        st.metric(
            label="Quality Score",
            value=f"{comparison.after_quality_score:.1f}",
            delta=f"{comparison.quality_score_diff:+.1f}" if comparison.quality_score_diff != 0 else None,
        )

    with st.expander("Detailed Comparison Table", expanded=False):
        st.dataframe(comparison.to_dataframe(), width="stretch", hide_index=True)
        if comparison.added_columns:
            st.write(f"**Added Columns:** {', '.join(comparison.added_columns)}")
        if comparison.removed_columns:
            st.write(f"**Removed Columns:** {', '.join(comparison.removed_columns)}")
        if comparison.dtype_changes:
            st.write("**Type Conversions:**")
            for col, chg in comparison.dtype_changes.items():
                st.write(f"- `{col}`: `{chg['before']}` ➜ `{chg['after']}`")

    st.markdown("---")

    # 2. Cleaned Data Exports
    st.subheader("💾 Download Cleaned Data")
    st.caption("Select your preferred format for the working dataset.")

    csv_data = generate_csv_report(work_df)
    excel_data = generate_excel_report(
        work_df,
        issues=issues,
        quality_summary=quality_summary,
        comparison=comparison,
        original_df=orig_df,
        history=history,
    )
    json_data = generate_json_export(work_df)

    base_name = getattr(bundle.file_meta, "name", "dataset").rsplit(".", 1)[0]

    dcol1, dcol2, dcol3 = st.columns(3)
    with dcol1:
        st.download_button(
            label="⬇️ Download CSV",
            data=csv_data,
            file_name=f"{base_name}_cleaned.csv",
            mime="text/csv",
            key="export_cleaned_csv",
            type="primary",
        )
    with dcol2:
        st.download_button(
            label="⬇️ Download Excel (.xlsx)",
            data=excel_data,
            file_name=f"{base_name}_cleaned.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_cleaned_excel",
        )
    with dcol3:
        st.download_button(
            label="⬇️ Download JSON",
            data=json_data,
            file_name=f"{base_name}_cleaned.json",
            mime="application/json",
            key="export_cleaned_json",
        )

    st.markdown("---")

    # 3. Reports & Audit Log
    st.subheader("📄 Reports & Audit Log")
    rcol1, rcol2, rcol3 = st.columns(3)

    pdf_data = generate_pdf_report(
        work_df,
        quality_summary=quality_summary,
        issues=issues,
        comparison=comparison,
        original_df=orig_df,
        history=history,
    )
    log_csv = generate_cleaning_log_export(history, "csv")
    log_json = generate_cleaning_log_export(history, "json")

    with rcol1:
        st.markdown("**Comprehensive Report (PDF)**")
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_data,
            file_name=f"{base_name}_quality_report.pdf",
            mime="application/pdf",
            key="export_report_pdf",
        )
    with rcol2:
        st.markdown("**Multi-Sheet Report (Excel)**")
        st.download_button(
            label="📊 Download Excel Report",
            data=excel_data,
            file_name=f"{base_name}_full_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_full_excel",
        )
    with rcol3:
        st.markdown("**Cleaning Audit Log**")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.download_button(
                label="Log CSV",
                data=log_csv,
                file_name=f"{base_name}_cleaning_log.csv",
                mime="text/csv",
                key="export_log_csv",
            )
        with sc2:
            st.download_button(
                label="Log JSON",
                data=log_json,
                file_name=f"{base_name}_cleaning_log.json",
                mime="application/json",
                key="export_log_json",
            )

    st.markdown("---")

    # 4. Reproducible Pandas Script
    st.subheader("🐍 Reproducible Cleaning Script")
    st.caption("Standalone Python / pandas script replicating all transformations applied to this file.")

    script_text = generate_cleaning_script(
        history=history,
        input_filename=getattr(bundle.file_meta, "name", "dataset.csv"),
        output_filename=f"{base_name}_cleaned.csv",
    )

    st.download_button(
        label="⬇️ Download Python Script (.py)",
        data=script_text.encode("utf-8"),
        file_name=f"clean_{base_name}.py",
        mime="text/x-python",
        key="export_python_script",
    )

    with st.expander("View Generated Python Code", expanded=False):
        st.code(script_text, language="python")

    st.markdown("---")

    # 5. Cleaning Recipe (JSON)
    st.subheader("📖 Cleaning Recipe (JSON)")
    st.caption("Save your cleaning operations as a portable JSON recipe to automate future datasets with identical schemas.")
    from core.recipes import save_recipe
    recipe_json_str = save_recipe(
        history,
        name=f"{base_name}_recipe",
        target_columns=list(work_df.columns),
        description=f"Automated cleaning pipeline recipe for {base_name}.",
    )
    st.download_button(
        label="⬇️ Download Cleaning Recipe (.json)",
        data=recipe_json_str.encode("utf-8"),
        file_name=f"{base_name}_recipe.json",
        mime="application/json",
        key="export_recipe_json_btn",
    )

    st.markdown("</div>", unsafe_allow_html=True)
