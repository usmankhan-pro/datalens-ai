"""Reports page — PDF, Excel, CSV report generation."""

import streamlit as st

from core.reporting import generate_csv_report, generate_excel_report, generate_pdf_report
from core.utils.state import get_bundle, has_dataset


def page() -> None:
    """Render the Reports page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📄 Reports")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">📄</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to generate PDF, Excel, and CSV reports.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for report generation.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = bundle.working_df if hasattr(bundle, "working_df") else bundle.original_df
    quality_summary = bundle.quality_result or {"overall_score": 100.0}
    issues = quality_summary.get("issues", []) if isinstance(quality_summary, dict) else []

    st.subheader("Generate Report")
    st.caption("Reusable exports for the current working dataset.")

    if st.button("Generate Report", type="primary", key="report_generate_button"):
        pdf_bytes = generate_pdf_report(df, quality_summary=quality_summary, issues=issues)
        excel_bytes = generate_excel_report(df, issues=issues, quality_summary=quality_summary)
        csv_bytes = generate_csv_report(df, issues=issues)

        st.success("Report generated successfully.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                "Download PDF",
                data=pdf_bytes,
                file_name="datalens_report.pdf",
                mime="application/pdf",
            )
        with col2:
            st.download_button(
                "Download Excel",
                data=excel_bytes,
                file_name="datalens_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with col3:
            st.download_button(
                "Download CSV",
                data=csv_bytes,
                file_name="datalens_report.csv",
                mime="text/csv",
            )

    st.markdown("</div>", unsafe_allow_html=True)
