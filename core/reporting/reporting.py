"""Report generation and export helpers for DataLens AI."""

from __future__ import annotations

import io
import json
from typing import Any, Dict, List, Optional, Sequence

import pandas as pd
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from core.export.comparator import DatasetComparison, compare_datasets


def generate_csv_report(df: pd.DataFrame, issues: Sequence[Dict[str, Any]] | None = None) -> bytes:
    """Export the current dataset to CSV bytes."""
    if df is None or df.empty:
        return b""

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def generate_json_export(df: pd.DataFrame, orient: str = "records") -> bytes:
    """Export the current dataset to JSON bytes."""
    if df is None or df.empty:
        return b"[]"

    json_str = df.to_json(orient=orient, date_format="iso", indent=2)
    return json_str.encode("utf-8")


def generate_cleaning_log_export(history: Sequence[Any], export_format: str = "csv") -> bytes:
    """Export the cleaning audit log to CSV or JSON bytes."""
    records = []
    for item in history or []:
        if isinstance(item, dict):
            records.append(item)
        else:
            records.append({
                "timestamp": getattr(item, "timestamp", ""),
                "operation": getattr(item, "operation", ""),
                "columns": ", ".join(getattr(item, "columns", [])) if getattr(item, "columns", None) else "",
                "rows_affected": getattr(item, "rows_affected", 0),
                "params": json.dumps(getattr(item, "params", {})),
            })

    log_df = pd.DataFrame(records)
    if export_format.lower() == "json":
        return log_df.to_json(orient="records", indent=2).encode("utf-8")

    csv_buffer = io.StringIO()
    log_df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8")


def generate_excel_report(
    df: pd.DataFrame,
    issues: Sequence[Dict[str, Any]] | None = None,
    insights: Sequence[Dict[str, Any]] | None = None,
    quality_summary: Dict[str, Any] | None = None,
    comparison: Optional[DatasetComparison] = None,
    original_df: Optional[pd.DataFrame] = None,
    history: Sequence[Any] | None = None,
) -> bytes:
    """Generate an Excel workbook including comparison, summary, issues, log, and cleaned data sheets."""
    buffer = io.BytesIO()
    workbook = xlsxwriter.Workbook(buffer)
    styles = {
        "header": workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1}),
        "body": workbook.add_format({"border": 1}),
        "title": workbook.add_format({"bold": True, "font_size": 14}),
        "diff_pos": workbook.add_format({"border": 1, "bg_color": "#E2EFDA", "font_color": "#375623"}),
        "diff_neg": workbook.add_format({"border": 1, "bg_color": "#FCE4D6", "font_color": "#C65911"}),
    }

    # 1. Summary sheet
    summary = workbook.add_worksheet("Summary")
    summary.write(0, 0, "DataLens AI Data Quality & Export Report", styles["title"])
    summary.write(2, 0, "Cleaned Rows", styles["header"])
    summary.write(2, 1, int(len(df)) if df is not None else 0, styles["body"])
    summary.write(3, 0, "Cleaned Columns", styles["header"])
    summary.write(3, 1, int(len(df.columns)) if df is not None else 0, styles["body"])

    quality_score = 100.0
    if quality_summary and isinstance(quality_summary, dict):
        quality_score = float(quality_summary.get("overall_score", quality_score))
    summary.write(4, 0, "Quality Score", styles["header"])
    summary.write(4, 1, round(quality_score, 1), styles["body"])

    # 2. Before / After Comparison sheet
    comp = comparison
    if comp is None and original_df is not None and df is not None:
        comp = compare_datasets(original_df, df, after_score=quality_score)

    if comp is not None:
        comp_sheet = workbook.add_worksheet("Before_After_Comparison")
        comp_sheet.write(0, 0, "Before vs. After Cleaning Metrics", styles["title"])
        headers = ["Metric", "Before", "After", "Change"]
        for c_idx, h in enumerate(headers):
            comp_sheet.write(2, c_idx, h, styles["header"])

        metrics_data = [
            ("Rows", comp.before_rows, comp.after_rows, comp.rows_diff),
            ("Columns", comp.before_cols, comp.after_cols, comp.cols_diff),
            ("Missing (%)", round(comp.before_missing_pct, 2), round(comp.after_missing_pct, 2), round(comp.missing_pct_diff, 2)),
            ("Duplicates", comp.before_duplicates, comp.after_duplicates, comp.duplicates_diff),
            ("Quality Score", round(comp.before_quality_score, 1), round(comp.after_quality_score, 1), round(comp.quality_score_diff, 1)),
        ]
        for r_idx, (m, b_val, a_val, diff) in enumerate(metrics_data, start=3):
            comp_sheet.write(r_idx, 0, m, styles["body"])
            comp_sheet.write(r_idx, 1, b_val, styles["body"])
            comp_sheet.write(r_idx, 2, a_val, styles["body"])
            diff_style = styles["diff_pos"] if diff > 0 else (styles["diff_neg"] if diff < 0 else styles["body"])
            comp_sheet.write(r_idx, 3, diff, diff_style)

    # 3. Cleaning Log sheet
    if history:
        log_sheet = workbook.add_worksheet("Cleaning_Log")
        log_headers = ["Step", "Timestamp", "Operation", "Columns", "Rows Affected", "Parameters"]
        for c_idx, h in enumerate(log_headers):
            log_sheet.write(0, c_idx, h, styles["header"])
        for r_idx, item in enumerate(history, start=1):
            log_sheet.write(r_idx, 0, r_idx, styles["body"])
            log_sheet.write(r_idx, 1, getattr(item, "timestamp", str(item.get("timestamp", "") if isinstance(item, dict) else "")), styles["body"])
            log_sheet.write(r_idx, 2, getattr(item, "operation", str(item.get("operation", "") if isinstance(item, dict) else "")), styles["body"])
            cols_val = getattr(item, "columns", item.get("columns", []) if isinstance(item, dict) else [])
            log_sheet.write(r_idx, 3, ", ".join(cols_val) if isinstance(cols_val, list) else str(cols_val), styles["body"])
            log_sheet.write(r_idx, 4, getattr(item, "rows_affected", int(item.get("rows_affected", 0) if isinstance(item, dict) else 0)), styles["body"])
            params_val = getattr(item, "params", item.get("params", {}) if isinstance(item, dict) else {})
            log_sheet.write(r_idx, 5, json.dumps(params_val), styles["body"])

    # 4. Issues sheet
    issues_sheet = workbook.add_worksheet("Issues")
    issue_rows = list(issues or [])
    issue_columns = ["type", "column", "severity", "affected_rows", "affected_pct"]
    for col_idx, name in enumerate(issue_columns):
        issues_sheet.write(0, col_idx, name, styles["header"])
    for row_idx, issue in enumerate(issue_rows, start=1):
        for col_idx, name in enumerate(issue_columns):
            issues_sheet.write(row_idx, col_idx, issue.get(name, ""), styles["body"])

    # 5. Cleaned Data sheet
    data_sheet = workbook.add_worksheet("Cleaned_Data")
    if df is not None and not df.empty:
        for col_idx, column_name in enumerate(df.columns.tolist()):
            data_sheet.write(0, col_idx, str(column_name), styles["header"])
        for row_idx, row in enumerate(df.itertuples(index=False, name=None), start=1):
            for col_idx, value in enumerate(row):
                # xlsxwriter cannot write NaNs directly without error or empty string
                val = "" if pd.isna(value) else value
                data_sheet.write(row_idx, col_idx, val, styles["body"])

    workbook.close()
    return buffer.getvalue()


def generate_pdf_report(
    df: pd.DataFrame,
    quality_summary: Dict[str, Any] | None = None,
    issues: Sequence[Dict[str, Any]] | None = None,
    insights: Sequence[Dict[str, Any]] | None = None,
    comparison: Optional[DatasetComparison] = None,
    original_df: Optional[pd.DataFrame] = None,
    history: Sequence[Any] | None = None,
) -> bytes:
    """Generate a comprehensive PDF report summarizing dataset health, comparison, and findings."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story: List[Any] = []
    styles = getSampleStyleSheet()

    title = "DataLens AI Data Quality & Analytics Report"
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 10))

    cur_rows = len(df) if df is not None else 0
    cur_cols = len(df.columns) if df is not None else 0
    story.append(Paragraph(f"<b>Cleaned Dataset Size:</b> {cur_rows:,} rows × {cur_cols} columns", styles["BodyText"]))

    quality_score = 100.0
    if quality_summary and isinstance(quality_summary, dict):
        quality_score = float(quality_summary.get("overall_score", quality_score))
    story.append(Paragraph(f"<b>Overall Quality Score:</b> {quality_score:.1f} / 100", styles["BodyText"]))
    story.append(Spacer(1, 12))

    # Before / After Comparison Table
    comp = comparison
    if comp is None and original_df is not None and df is not None:
        comp = compare_datasets(original_df, df, after_score=quality_score)

    if comp is not None:
        story.append(Paragraph("Before vs. After Cleaning Comparison", styles["Heading2"]))
        comp_table_data = [
            ["Metric", "Before", "After", "Change"],
            ["Rows", f"{comp.before_rows:,}", f"{comp.after_rows:,}", f"{comp.rows_diff:+d}"],
            ["Columns", f"{comp.before_cols}", f"{comp.after_cols}", f"{comp.cols_diff:+d}"],
            ["Missing %", f"{comp.before_missing_pct:.1f}%", f"{comp.after_missing_pct:.1f}%", f"{comp.missing_pct_diff:+.1f}%"],
            ["Duplicates", f"{comp.before_duplicates:,}", f"{comp.after_duplicates:,}", f"{comp.duplicates_diff:+d}"],
            ["Quality Score", f"{comp.before_quality_score:.1f}", f"{comp.after_quality_score:.1f}", f"{comp.quality_score_diff:+.1f}"],
        ]
        t = Table(comp_table_data, colWidths=[130, 90, 90, 90])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D9EAF7")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

    # Cleaning Log Summary
    if history:
        story.append(Paragraph("Cleaning Operations Applied", styles["Heading2"]))
        log_table_data = [["#", "Operation", "Rows Affected", "Details"]]
        for idx, item in enumerate(history[:8], start=1):
            op = getattr(item, "operation", str(item.get("operation", "") if isinstance(item, dict) else ""))
            aff = getattr(item, "rows_affected", int(item.get("rows_affected", 0) if isinstance(item, dict) else 0))
            params = getattr(item, "params", item.get("params", {}) if isinstance(item, dict) else {})
            param_str = ", ".join(f"{k}={v}" for k, v in list(params.items())[:2]) if params else "default"
            log_table_data.append([str(idx), op, f"{aff:,}", param_str])

        log_t = Table(log_table_data, colWidths=[25, 150, 90, 150])
        log_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        story.append(log_t)
        story.append(Spacer(1, 12))

    # Top Quality Issues
    if issues:
        story.append(Paragraph("Quality Issues", styles["Heading2"]))
        issue_table = [["Type", "Column", "Severity", "Affected %"]]
        for issue in list(issues)[:10]:
            aff_pct = issue.get("affected_pct", 0)
            aff_str = f"{aff_pct:.1f}%" if isinstance(aff_pct, (int, float)) else str(aff_pct)
            issue_table.append([
                str(issue.get("type", "")),
                str(issue.get("column", "")),
                str(issue.get("severity", "")),
                aff_str,
            ])
        it = Table(issue_table, colWidths=[120, 110, 80, 80])
        it.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        story.append(it)
    else:
        story.append(Paragraph("No quality issues detected.", styles["BodyText"]))

    if insights:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Key Insights", styles["Heading2"]))
        for insight in list(insights)[:5]:
            text = insight.get('text', '') if isinstance(insight, dict) else str(insight)
            story.append(Paragraph(f"• {text}", styles["BodyText"]))

    # Legal / Operational Disclaimer
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "<i>Disclaimer: Quality scores and analytical metrics are rule-based decision support indicators, "
        "not proof of fitness or absence of real-world errors. Always verify critical business logic.</i>",
        styles["Italic"]
    ))

    doc.build(story)
    return buffer.getvalue()


__all__ = [
    "generate_csv_report",
    "generate_json_export",
    "generate_cleaning_log_export",
    "generate_excel_report",
    "generate_pdf_report",
]
