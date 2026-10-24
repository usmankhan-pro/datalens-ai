"""Unit tests for Stage 1: Export, Comparison, and Script Generation."""

import io
import json
import numpy as np
import pandas as pd
import pytest

from core.export.comparator import compare_datasets, DatasetComparison
from core.export.script_generator import generate_cleaning_script
from core.reporting.reporting import (
    generate_csv_report,
    generate_json_export,
    generate_cleaning_log_export,
    generate_excel_report,
    generate_pdf_report,
)
from core.utils.state import TransformRecord


def test_compare_datasets_basic():
    before_df = pd.DataFrame({
        "id": [1, 2, 2, 3],
        "name": ["Alice", "Bob", "Bob", None],
        "val": [10.0, 20.0, 20.0, np.nan],
    })
    after_df = pd.DataFrame({
        "id": [1, 2, 3],
        "name": ["Alice", "Bob", "Charlie"],
        "val": [10.0, 20.0, 30.0],
    })

    comp = compare_datasets(before_df, after_df)

    assert comp.before_rows == 4
    assert comp.after_rows == 3
    assert comp.rows_diff == -1

    assert comp.before_cols == 3
    assert comp.after_cols == 3
    assert comp.cols_diff == 0

    assert comp.before_duplicates == 1
    assert comp.after_duplicates == 0
    assert comp.duplicates_diff == -1

    assert comp.before_missing_cells == 2
    assert comp.after_missing_cells == 0
    assert comp.after_missing_pct == 0.0
    assert comp.missing_pct_diff < 0  # Missing % reduced

    df_summary = comp.to_dataframe()
    assert isinstance(df_summary, pd.DataFrame)
    assert "Metric" in df_summary.columns
    assert "Change" in df_summary.columns


def test_compare_datasets_column_changes():
    before_df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    after_df = pd.DataFrame({"a": [1.0, 2.0], "c": [True, False]})

    comp = compare_datasets(before_df, after_df)
    assert "b" in comp.removed_columns
    assert "c" in comp.added_columns
    assert "a" in comp.dtype_changes


def test_generate_cleaning_script_compilation():
    history = [
        TransformRecord(
            timestamp="2026-10-24 12:00:00",
            operation="drop_duplicates",
            columns=["id", "val"],
            params={"keep": "first"},
            rows_affected=1,
        ),
        TransformRecord(
            timestamp="2026-10-24 12:01:00",
            operation="snake_case_columns",
            columns=[],
            params={},
            rows_affected=0,
        ),
        TransformRecord(
            timestamp="2026-10-24 12:02:00",
            operation="fill_missing_numeric",
            columns=["val"],
            params={"method": "median", "columns": ["val"]},
            rows_affected=2,
        ),
        TransformRecord(
            timestamp="2026-10-24 12:03:00",
            operation="standardize_text",
            columns=["name"],
            params={"case": "lower", "strip": True, "columns": ["name"]},
            rows_affected=3,
        ),
        TransformRecord(
            timestamp="2026-10-24 12:04:00",
            operation="replace_placeholders",
            columns=[],
            params={"placeholders": ["N/A", "999"]},
            rows_affected=1,
        ),
        TransformRecord(
            timestamp="2026-10-24 12:05:00",
            operation="cap_outliers",
            columns=["val"],
            params={"method": "iqr", "factor": 1.5, "columns": ["val"]},
            rows_affected=1,
        ),
    ]

    script = generate_cleaning_script(history, input_filename="test.csv", output_filename="out.csv")

    assert isinstance(script, str)
    assert "def clean_dataset" in script
    assert "drop_duplicates" in script
    assert "fillna" in script
    assert "out.csv" in script

    # Verify script compiles without syntax errors
    compiled = compile(script, "<test_script>", "exec")
    assert compiled is not None


def test_generate_json_and_cleaning_log_export():
    df = pd.DataFrame({"id": [1, 2], "score": [95.5, 88.0]})
    json_bytes = generate_json_export(df)
    assert isinstance(json_bytes, bytes)
    parsed = json.loads(json_bytes.decode("utf-8"))
    assert len(parsed) == 2
    assert parsed[0]["score"] == 95.5

    history = [
        {"timestamp": "2026-10-24", "operation": "drop_duplicates", "rows_affected": 2, "params": {}},
    ]
    csv_log = generate_cleaning_log_export(history, export_format="csv")
    assert b"drop_duplicates" in csv_log

    json_log = generate_cleaning_log_export(history, export_format="json")
    parsed_log = json.loads(json_log.decode("utf-8"))
    assert len(parsed_log) == 1
    assert parsed_log[0]["operation"] == "drop_duplicates"


def test_excel_and_pdf_reports():
    orig_df = pd.DataFrame({"a": [1, 2, 2], "b": ["x", "y", "y"]})
    cleaned_df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    history = [
        {"timestamp": "2026-10-24", "operation": "drop_duplicates", "rows_affected": 1, "params": {}}
    ]

    excel_bytes = generate_excel_report(
        cleaned_df,
        original_df=orig_df,
        history=history,
        issues=[{"type": "duplicate_rows", "column": "all", "severity": "LOW", "affected_pct": 33.3}],
    )
    assert len(excel_bytes) > 0

    pdf_bytes = generate_pdf_report(
        cleaned_df,
        original_df=orig_df,
        history=history,
        issues=[{"type": "duplicate_rows", "column": "all", "severity": "LOW", "affected_pct": 33.3}],
        insights=[{"text": "Data quality improved significantly after duplicate removal."}],
    )
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF")
