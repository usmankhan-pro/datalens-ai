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
