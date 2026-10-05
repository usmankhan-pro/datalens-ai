"""Report generation helpers for DataLens AI."""

from __future__ import annotations

import io
from typing import Any, Dict, Iterable, List, Sequence

import pandas as pd
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_csv_report(df: pd.DataFrame, issues: Sequence[Dict[str, Any]] | None = None) -> bytes:
    """Export the current dataset to CSV bytes."""
    if df is None or df.empty:
        return b""

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def generate_excel_report(
    df: pd.DataFrame,
    issues: Sequence[Dict[str, Any]] | None = None,
    insights: Sequence[Dict[str, Any]] | None = None,
    quality_summary: Dict[str, Any] | None = None,
) -> bytes:
    """Generate an Excel workbook including a summary, issues, and cleaned data sheets."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer)
    styles = {
        "header": workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1}),
        "body": workbook.add_format({"border": 1}),
        "title": workbook.add_format({"bold": True, "font_size": 14}),
    }

    summary = workbook.add_worksheet("Summary")
    summary.write(0, 0, "DataLens AI Report", styles["title"])
    summary.write(2, 0, "Rows", styles["header"])
    summary.write(2, 1, int(len(df)) if df is not None else 0, styles["body"])
    summary.write(3, 0, "Columns", styles["header"])
    summary.write(3, 1, int(len(df.columns)) if df is not None else 0, styles["body"])
    quality_score = 100.0
    if quality_summary and isinstance(quality_summary, dict):
        quality_score = float(quality_summary.get("overall_score", quality_score))
    summary.write(4, 0, "Quality Score", styles["header"])
    summary.write(4, 1, round(quality_score, 2), styles["body"])

    issues_sheet = workbook.add_worksheet("Issues")
    issue_rows = list(issues or [])
    issue_columns = ["type", "column", "severity", "affected_rows", "affected_pct"]
    for col_idx, name in enumerate(issue_columns):
        issues_sheet.write(0, col_idx, name, styles["header"])
    for row_idx, issue in enumerate(issue_rows, start=1):
        for col_idx, name in enumerate(issue_columns):
            issues_sheet.write(row_idx, col_idx, issue.get(name, ""), styles["body"])

    data_sheet = workbook.add_worksheet("Cleaned_Data")
    for col_idx, column_name in enumerate(df.columns.tolist()):
        data_sheet.write(0, col_idx, column_name, styles["header"])
    for row_idx, row in enumerate(df.itertuples(index=False, name=None), start=1):
        for col_idx, value in enumerate(row):
            data_sheet.write(row_idx, col_idx, value, styles["body"])

    workbook.close()
    return buffer.getvalue()


def generate_pdf_report(
    df: pd.DataFrame,
    quality_summary: Dict[str, Any] | None = None,
    issues: Sequence[Dict[str, Any]] | None = None,
    insights: Sequence[Dict[str, Any]] | None = None,
) -> bytes:
    """Generate a lightweight PDF report summarizing the dataset and findings."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story: List[Any] = []
    styles = getSampleStyleSheet()

    title = "DataLens AI Report"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Rows: {len(df)} | Columns: {len(df.columns)}", styles["BodyText"]))

    quality_score = 100.0
    if quality_summary and isinstance(quality_summary, dict):
        quality_score = float(quality_summary.get("overall_score", quality_score))
    story.append(Paragraph(f"Quality Score: {quality_score:.1f}", styles["BodyText"]))
    story.append(Spacer(1, 12))

    if issues:
        issue_table = [["Type", "Column", "Severity", "Affected %"]]
        for issue in list(issues)[:10]:
            issue_table.append([
                issue.get("type", ""),
                issue.get("column", ""),
                issue.get("severity", ""),
                issue.get("affected_pct", 0),
            ])
        story.append(Paragraph("Top Issues", styles["Heading2"]))
        story.append(Table(issue_table, colWidths=[110, 110, 70, 70]))
    else:
        story.append(Paragraph("No quality issues detected.", styles["BodyText"]))

    if insights:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Key Insights", styles["Heading2"]))
        for insight in list(insights)[:5]:
            story.append(Paragraph(f"- {insight.get('text', '')}", styles["BodyText"]))

    doc.build(story)
    return buffer.getvalue()


__all__ = ["generate_csv_report", "generate_excel_report", "generate_pdf_report"]
