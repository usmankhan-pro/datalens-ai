from io import BytesIO, StringIO
from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest

from app import csv_bytes, excel_bytes, load_demo, log_csv_bytes
from cleaning import clean_data
from src.reporting.export_manager import export_cleaned_dataset


def test_telco_csv_and_excel_round_trip_without_index():
    source = load_demo()
    cleaned, _ = clean_data(source, {"types": True}, {}, {})

    csv_data = pd.read_csv(StringIO(csv_bytes(cleaned).decode("utf-8")))
    excel_data = pd.read_excel(BytesIO(excel_bytes(cleaned)), engine="openpyxl")

    assert_frame_equal(csv_data, cleaned, check_dtype=False)
    assert_frame_equal(excel_data, cleaned, check_dtype=False)
    assert not any(column.startswith("Unnamed:") for column in csv_data.columns)
    assert not any(column.startswith("Unnamed:") for column in excel_data.columns)


def test_special_characters_survive_csv_excel_and_cleaning_log():
    source = pd.DataFrame({"city": ["Montréal", "東京"], "note": ["café", "naïve"]})
    log = [{"step": "Normalize", "column": "city 東京", "rows_affected": 1}]

    csv_data = pd.read_csv(StringIO(csv_bytes(source).decode("utf-8")))
    excel_data = pd.read_excel(BytesIO(excel_bytes(source)), engine="openpyxl")
    log_data = pd.read_csv(StringIO(log_csv_bytes(log).decode("utf-8")))

    assert csv_data.equals(source)
    assert excel_data.equals(source)
    assert log_data.loc[0, "column"] == "city 東京"


def test_log_export_has_columns_when_no_steps_are_applied():
    data = pd.read_csv(StringIO(log_csv_bytes([]).decode("utf-8")))

    assert list(data.columns) == ["step", "column", "rows_affected"]
    assert data.empty


def test_reports_workspace_shows_download_controls():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)
    app.session_state["active_workspace"] = "Reports & Export"
    app.run(timeout=30)

    labels = [button.label for button in app.get("download_button")]
    assert {"Download cleaned dataset (CSV)", "Download quality report (CSV)"}.issubset(labels)


def test_report_downloads_serialize_the_approved_working_dataset(monkeypatch):
    captured: dict[str, bytes] = {}
    original_export = export_cleaned_dataset

    def capture_export(data: pd.DataFrame, format: str = "csv"):
        payload, filename, mime = original_export(data, format)
        captured[format] = payload
        return payload, filename, mime

    monkeypatch.setattr("src.ui.export_cleaned_dataset", capture_export)
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    source = pd.DataFrame({"id": [1, 1, 2], "value": ["a", "a", "b"]})
    original = source.copy(deep=True)
    app.session_state["data"] = source
    app.session_state["source"] = "duplicate.csv"
    app.session_state["active_workspace"] = "Data Cleaning"
    app.run(timeout=30)

    app.button(key="FormSubmitter:cleaning_operation_form-Build transformation preview").click().run(timeout=30)
    app.button(key="approve_cleaning_preview").click().run(timeout=30)
    working = app.session_state["cleaning_pipeline"].working.copy(deep=True)
    app.radio[0].set_value("Reports & Export").run(timeout=30)

    csv_export = pd.read_csv(BytesIO(captured["csv"]))
    excel_export = pd.read_excel(BytesIO(captured["excel"]), engine="openpyxl")

    expected_export = working.reset_index(drop=True)
    pd.testing.assert_frame_equal(csv_export, expected_export, check_dtype=False)
    pd.testing.assert_frame_equal(excel_export, expected_export, check_dtype=False)
    pd.testing.assert_frame_equal(source, original)
    assert working.shape == (2, 2)
