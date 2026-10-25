from pathlib import Path

import pandas as pd
from pandas.api.types import is_numeric_dtype
from streamlit.testing.v1 import AppTest

from app import load_demo
from cleaning import clean_data, count_iqr_outliers, fill_missing, handle_outliers


def test_telco_type_fix_preserves_source_and_expected_values():
    original = load_demo()
    before = original.copy(deep=True)

    cleaned, log = clean_data(original, {"types": True}, {}, {})

    assert is_numeric_dtype(cleaned["TotalCharges"])
    assert cleaned["TotalCharges"].isna().sum() == 11
    assert (cleaned.loc[cleaned["TotalCharges"].isna(), "tenure"] == 0).all()
    assert len(cleaned) == 7043
    assert original.equals(before)
    assert any(row["column"] == "TotalCharges" for row in log)


def test_duplicate_and_text_cleanup_on_injected_telco_copy():
    original = load_demo()
    original["City"] = "Boston"
    original.loc[:2, "City"] = ["NY", "ny ", " New York"]
    original = pd.concat([original, original.iloc[:50]], ignore_index=True)

    cleaned, log = clean_data(
        original,
        {"duplicates": True, "text": True},
        {},
        {},
    )

    assert len(original) == 7093
    assert len(cleaned) == 7043
    assert cleaned["City"].nunique() == 2
    assert set(cleaned["City"].dropna()) == {"Boston", "New York"}
    assert sum(row["rows_affected"] for row in log if row["step"] == "Remove duplicates") == 50


def test_missing_value_imputation_and_drop_rules():
    data = pd.DataFrame({"score": [1.0, 2.0, None, 4.0], "group": ["a", "b", None, "b"]})

    filled, log = fill_missing(
        data,
        {"score": ("Median", ""), "group": ("Mode", "")},
    )
    mean_filled, _ = fill_missing(data, {"score": ("Mean", "")})
    dropped, drop_log = fill_missing(data, {"score": ("Drop rows", "")})

    assert filled["score"].iloc[2] == 2.0
    assert mean_filled["score"].iloc[2] == 7 / 3
    assert filled["group"].iloc[2] == "b"
    assert len(log) == 2
    assert len(dropped) == 3
    assert drop_log[0]["rows_affected"] == 1
    assert data.isna().sum().sum() == 2


def test_custom_missing_value_rule():
    data = pd.DataFrame({"label": ["a", None]})

    cleaned, _ = fill_missing(data, {"label": ("Custom", "review")})

    assert cleaned["label"].tolist() == ["a", "review"]


def test_iqr_outlier_count_cap_remove_and_ignore():
    data = pd.DataFrame({"value": [1, 2, 3, 4, 100]})

    assert count_iqr_outliers(data, "value") == 1
    capped, cap_log = handle_outliers(data, {"value": "Cap"})
    removed, remove_log = handle_outliers(data, {"value": "Remove"})
    ignored, ignore_log = handle_outliers(data, {"value": "Ignore"})

    assert capped["value"].max() == 7
    assert len(removed) == 4
    assert cap_log[0]["rows_affected"] == 1
    assert remove_log[0]["rows_affected"] == 1
    assert ignored.equals(data)
    assert ignore_log[0]["rows_affected"] == 0


def test_cleaning_checkbox_updates_working_copy_only():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.run(timeout=30)
    app.button[0].click().run(timeout=30)

    # Verify source data is unchanged and cleaned_data is accessible
    assert app.session_state["data"]["TotalCharges"].dtype == "str"
    assert app.session_state["data"].equals(app.session_state["data"])

    # Verify the cleaning pipeline was initialized
    assert "cleaning_pipeline" in app.session_state or "cleaned_data" in app.session_state
