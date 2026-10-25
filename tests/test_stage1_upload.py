from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest
from pandas.api.types import is_string_dtype
from streamlit.testing.v1 import AppTest

from app import load_demo, read_table


@pytest.fixture
def csv_source():
    def create(content: bytes) -> BytesIO:
        return BytesIO(content)

    return create


def test_telco_demo_matches_expected_overview():
    data = load_demo()

    assert data.shape == (7043, 21)
    assert data.duplicated().sum() == 0
    assert is_string_dtype(data["TotalCharges"].dtype)
    assert data["TotalCharges"].isna().sum() == 11


def test_empty_csv_reports_clear_error(csv_source):
    with pytest.raises(ValueError, match="empty"):
        read_table(csv_source(b""), "empty.csv")


def test_one_column_csv_loads(csv_source):
    data = read_table(csv_source(b"name\nAda\n"), "one-column.csv")

    assert data.shape == (1, 1)
    assert data.loc[0, "name"] == "Ada"


def test_365_value_single_column_csv_loads_without_inventing_columns(csv_source):
    content = b"Subscribers gained\n" + b"48\n" * 365

    data = read_table(csv_source(content), "subs.csv")

    assert data.shape == (365, 1)
    assert data.columns.tolist() == ["Subscribers gained"]
    assert data.iloc[0, 0] == 48


def test_headers_only_csv_loads_with_no_rows(csv_source):
    data = read_table(csv_source(b"name,value\n"), "headers.csv")

    assert data.shape == (0, 2)
    assert list(data.columns) == ["name", "value"]


def test_excel_upload_loads_in_memory():
    source = BytesIO()
    pd.DataFrame({"name": ["Ada"]}).to_excel(source, index=False)
    source.seek(0)

    data = read_table(source, "data.xlsx")

    assert data.to_dict("records") == [{"name": "Ada"}]


def test_app_demo_button_loads_telco_data():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)

    assert app.session_state["data"].shape == (7043, 21)
    assert app.session_state["data"]["TotalCharges"].isna().sum() == 11


def test_first_launch_upload_starts_shared_analysis_workflow():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)

    assert app.session_state["active_workspace"] == "Dashboard"
    assert len(app.file_uploader) == 1
    assert any("Step 1 · Load your dataset" in item.value for item in app.subheader)

    app.file_uploader[0].upload(
        "sales.csv",
        b"amount;region\n10;East\n20;West\n",
        "text/csv",
    ).run(timeout=30)
    app.button(key="preview_source_file").click().run(timeout=30)
    app.button(key="confirm_dataset_replacement").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["active_workspace"] == "Dashboard"
    assert app.session_state["cleaning_pipeline"].working.to_dict("records") == [
        {"amount": 10, "region": "East"},
        {"amount": 20, "region": "West"},
    ]
    next(button for button in app.button if button.label == "Start with data quality").click().run(timeout=30)
    assert app.session_state["active_workspace"] == "Data Quality"
    assert app.session_state["cleaning_pipeline"].working.shape == (2, 2)
    app.button(key="workflow_next").click().run(timeout=30)
    assert app.session_state["active_workspace"] == "Data Cleaning"
    assert app.session_state["cleaning_pipeline"].working.shape == (2, 2)


def test_uploaded_dataset_drives_eda_cleaning_and_insights():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)
    content = (
        "record_id;amount;segment;event_date\n"
        "1;10;A;2025-01-01\n"
        "1;10;A;2025-01-01\n"
        "2;100;B;2025-01-02\n"
        "3;;A;2025-01-03\n"
    ).encode()
    app.file_uploader[0].upload("analysis.csv", content, "text/csv").run(timeout=30)
    app.button(key="preview_source_file").click().run(timeout=30)
    app.button(key="confirm_dataset_replacement").click().run(timeout=30)

    source_snapshot = app.session_state["original_data"].copy(deep=True)
    expected = pd.DataFrame(
        {
            "record_id": [1, 1, 2, 3],
            "amount": [10, 10, 100, None],
            "segment": ["A", "A", "B", "A"],
            "event_date": ["2025-01-01", "2025-01-01", "2025-01-02", "2025-01-03"],
        }
    )
    pd.testing.assert_frame_equal(source_snapshot, expected, check_dtype=False)

    app.radio[0].set_value("Exploratory Data Analysis (EDA)").run(timeout=30)
    assert not app.exception, [error.message for error in app.exception]
    assert app.session_state["cleaning_pipeline"].working.equals(source_snapshot)
    assert any("4" in str(metric.value) for metric in app.metric)
    assert any(
        "record_id" in str(option)
        for selectbox in app.selectbox
        for option in selectbox.options
    )
    for page in ["Data Quality", "Data Visualization", "Reports & Export"]:
        app.radio[0].set_value(page).run(timeout=30)
        assert not app.exception, (page, [error.message for error in app.exception])
        assert app.session_state["cleaning_pipeline"].working.equals(source_snapshot)

    app.radio[0].set_value("Data Cleaning").run(timeout=30)
    assert not app.exception, [error.message for error in app.exception]
    assert any("2 rows participate in exact duplicates" in element.value for element in app.markdown)
    app.button(key="FormSubmitter:cleaning_operation_form-Build transformation preview").click().run(timeout=30)
    preview = app.session_state["cleaning_preview"]
    assert preview["data"].shape == (3, 4)
    assert preview["records"][0].rows_affected == 1
    app.button(key="approve_cleaning_preview").click().run(timeout=30)

    assert app.session_state["cleaning_pipeline"].working.shape == (3, 4)
    assert app.session_state["original_data"].equals(source_snapshot)
    app.radio[0].set_value("Insights & Recommendations").run(timeout=30)
    assert not app.exception, [error.message for error in app.exception]
    assert app.session_state["cleaning_pipeline"].working.shape == (3, 4)
    assert any("Insights & Recommendations" in title.value for title in app.title)
    assert any(
        "Shared working dataset: analysis.csv" in caption.value
        for caption in app.caption
    )


def test_upload_from_eda_keeps_user_on_eda_with_loaded_dataset():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.session_state["active_workspace"] = "Exploratory Data Analysis (EDA)"
    app.run(timeout=30)

    app.file_uploader[0].upload(
        "measurements.csv",
        b"measure;group\n1;A\n2;B\n3;A\n",
        "text/csv",
    ).run(timeout=30)
    app.button(key="preview_source_file").click().run(timeout=30)
    assert any("Upload preview ready" in caption.value for caption in app.caption)

    app.button(key="confirm_dataset_replacement").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["active_workspace"] == "Exploratory Data Analysis (EDA)"
    assert app.session_state["cleaning_pipeline"].working.shape == (3, 2)
    assert any("Univariate and descriptive analysis" in item.value for item in app.subheader)


def test_sidebar_navigation_preserves_the_active_dataset():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)
    original = app.session_state["original_data"].copy(deep=True)
    pipeline = app.session_state["cleaning_pipeline"]

    for page in [
        "Data Quality",
        "Data Cleaning",
        "Data Visualization",
        "Exploratory Data Analysis (EDA)",
        "Insights & Recommendations",
        "Reports & Export",
        "Data Source & Settings",
        "Dashboard",
    ]:
        app.radio[0].set_value(page).run(timeout=60)
        assert not app.exception, (page, [error.message for error in app.exception])
        assert app.session_state["active_workspace"] == page
        assert any(page in str(element.value) for element in app.title)
        assert app.session_state["cleaning_pipeline"] is pipeline
        assert app.session_state["original_data"].equals(original)
        assert app.session_state["cleaning_pipeline"].working.shape == original.shape


def test_confirmed_dataset_replacement_resets_dataset_scoped_state():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.session_state["data"] = pd.DataFrame({"old_column": [1, 2]})
    app.session_state["source"] = "old.csv"
    app.session_state["analysis_cache"] = {(0, "overview"): {"old": True}}
    app.session_state["cleaning_preview"] = {"operation": "stale"}
    app.run(timeout=30)
    previous_workspace_id = app.session_state["workspace_id"]
    app.radio[0].set_value("Data Source & Settings").run(timeout=30)

    app.file_uploader[0].upload(
        "replacement.csv",
        b"new_column;group\n10;A\n20;B\n",
        "text/csv",
    ).run(timeout=30)
    app.button(key="preview_source_file").click().run(timeout=30)

    assert app.session_state["cleaning_pipeline"].working.columns.tolist() == [
        "old_column"
    ]
    assert any("Validated file preview" in element.value for element in app.subheader)

    app.button(key="confirm_dataset_replacement").click().run(timeout=30)

    assert not app.exception
    assert app.session_state["source"] == "replacement.csv"
    assert app.session_state["workspace_id"] != previous_workspace_id
    assert app.session_state["workspace_revision"] == 0
    assert app.session_state["cleaning_pipeline"].working.to_dict("records") == [
        {"new_column": 10, "group": "A"},
        {"new_column": 20, "group": "B"},
    ]
    assert app.session_state["original_data"].equals(
        app.session_state["cleaning_pipeline"].working
    )
    assert app.session_state["analysis_cache"][(0, "overview")]["n_rows"] == 2
    assert app.session_state["analysis_cache"][(0, "issues")] == []
    assert "cleaning_preview" not in app.session_state
    assert app.session_state["cleaning_pipeline"].records == []

    app.radio[0].set_value("Data Visualization").run(timeout=30)

    assert not app.exception
    chart_x_key = f"chart_x_{app.session_state['workspace_id']}"
    assert app.session_state[chart_x_key] == "new_column"
    assert all(
        option in {"new_column", "group"}
        for element in app.selectbox
        for option in element.options
        if element.key == chart_x_key
    )
