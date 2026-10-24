"""Unit tests for Stage 2: 8-Stage Cleaning Pipeline and State Undo."""

import numpy as np
import pandas as pd
import pytest

from core.cleaning.pipeline import (
    auto_clean_safe_steps,
    clean_duplicates_remove,
    clean_invalid_placeholders,
    clean_missing_drop_columns,
    clean_missing_impute,
    clean_outliers_cap,
    clean_outliers_remove,
    clean_structure_drop_empty_columns,
    clean_structure_drop_empty_rows,
    clean_structure_snake_case_names,
    clean_text_harmonize_variants,
    clean_text_standardize,
    clean_types_booleans,
    clean_types_dates,
    clean_types_numeric_text,
    clean_validate_dataset,
    detect_outliers_iqr,
    preview_operation,
    apply_operation,
)
from core.utils.state import DatasetBundle, FileMeta


@pytest.fixture
def messy_dataframe():
    """Create a representative messy DataFrame covering all 8 stages."""
    return pd.DataFrame({
        "Full Name": [" Alice Smith ", "BOB JONES", "Charlie Brown", "Charlie Brown", np.nan],
        "Gross Salary": ["$5,000", "$6,500.50", "(500)", "N/A", np.nan],
        "Join Date": ["2022-01-15", "2021/05/20", "2023-11-01", "2023-11-01", np.nan],
        "Is Active": ["Yes", "no", "TRUE", "false", np.nan],
        "Country": ["USA", "U.S.", "United States", "United States", np.nan],
        "Score": [10.0, 15.0, 999.0, 15.0, np.nan],
        "EmptyCol": [np.nan, np.nan, np.nan, np.nan, np.nan],
    })


def test_stage1_structure(messy_dataframe):
    # messy_dataframe already has 1 all-nan row at index 4; appending another makes 2
    all_nan_row = pd.DataFrame([[np.nan] * len(messy_dataframe.columns)], columns=messy_dataframe.columns)
    df_with_empty_row = pd.concat([messy_dataframe, all_nan_row], ignore_index=True)
    df_no_empty_rows, rows_dropped = clean_structure_drop_empty_rows(df_with_empty_row, how="all")
    assert rows_dropped == 2

    # Drop empty columns
    df_no_empty_cols, cols_dropped = clean_structure_drop_empty_columns(messy_dataframe)
    assert cols_dropped == 1
    assert "EmptyCol" not in df_no_empty_cols.columns

    # Snake case column names
    df_snake, name_changes = clean_structure_snake_case_names(messy_dataframe)
    assert "full_name" in df_snake.columns
    assert "gross_salary" in df_snake.columns
    assert "join_date" in df_snake.columns
    assert "is_active" in df_snake.columns


def test_stage2_types():
    df = pd.DataFrame({
        "salary": ["$1,200", "$2,500.50", "(100)"],
        "date_col": ["2022-01-01", "2022-02-01", "2022-03-01"],
        "active": ["yes", "no", "true"],
    })
    # Numeric text
    num_df, num_aff = clean_types_numeric_text(df, columns=["salary"])
    assert pd.api.types.is_numeric_dtype(num_df["salary"])
    assert num_df["salary"].iloc[2] == -100.0

    # Dates
    date_df, date_aff = clean_types_dates(df, columns=["date_col"])
    assert pd.api.types.is_datetime64_any_dtype(date_df["date_col"])

    # Booleans
    bool_df, bool_aff = clean_types_booleans(df, columns=["active"])
    assert bool_df["active"].tolist() == [True, False, True]


def test_stage3_text():
    df = pd.DataFrame({
        "name": ["  Alice  ", "bob  jones", "CHARLIE"],
        "country": ["USA", "U.S.", "USA"],
    })
    std_df, aff = clean_text_standardize(df, columns=["name"], case="title", strip=True)
    assert std_df["name"].tolist() == ["Alice", "Bob Jones", "Charlie"]

    harm_df, harm_aff = clean_text_harmonize_variants(df, column="country", mapping={"U.S.": "USA"})
    assert harm_df["country"].tolist() == ["USA", "USA", "USA"]
    assert harm_aff == 1


def test_stage4_invalid_placeholders():
    df = pd.DataFrame({
        "status": ["active", "N/A", "-", "valid"],
        "val": [10.0, 999.0, 20.0, -999.0],
    })
    clean_df, aff = clean_invalid_placeholders(df)
    assert clean_df["status"].isna().sum() == 2
    assert clean_df["val"].isna().sum() == 2


def test_stage5_duplicates():
    df = pd.DataFrame({
        "id": [1, 2, 2, 3],
        "name": ["A", "B", "B", "C"],
    })
    clean_df, aff = clean_duplicates_remove(df)
    assert len(clean_df) == 3
    assert aff == 1


def test_stage6_missing():
    df = pd.DataFrame({
        "num": [10.0, np.nan, 30.0],
        "cat": ["A", np.nan, "A"],
        "all_null": [np.nan, np.nan, np.nan],
    })
    # Median impute
    imp_num, aff_num = clean_missing_impute(df, column="num", strategy="median")
    assert imp_num["num"].iloc[1] == 20.0
    assert imp_num["num"].isna().sum() == 0

    # Mode impute
    imp_cat, aff_cat = clean_missing_impute(df, column="cat", strategy="mode")
    assert imp_cat["cat"].iloc[1] == "A"

    # Drop heavy missing columns
    drop_col_df, dropped_cols = clean_missing_drop_columns(df, threshold_pct=50.0)
    assert "all_null" not in drop_col_df.columns
    assert dropped_cols == 1


def test_stage7_outliers():
    # Distribution with an extreme outlier
    data = [10.0, 11.0, 10.5, 12.0, 11.5, 10.8, 11.2, 500.0]
    df = pd.DataFrame({"metric": data})

    mask = detect_outliers_iqr(df["metric"], factor=1.5)
    assert mask.iloc[-1] == True
    assert mask.sum() == 1

    # Cap outliers
    capped_df, cap_cnt = clean_outliers_cap(df, columns=["metric"], factor=1.5)
    assert cap_cnt == 1
    assert capped_df["metric"].max() < 500.0

    # Remove outliers
    removed_df, rem_cnt = clean_outliers_remove(df, columns=["metric"], factor=1.5)
    assert rem_cnt == 1
    assert len(removed_df) == 7


def test_stage8_validation():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    val = clean_validate_dataset(df)
    assert val["valid"] is True
    assert val["rows"] == 2
    assert val["cols"] == 2
    assert val["missing_cells"] == 0


def test_auto_clean_safe_steps(messy_dataframe):
    # Auto-clean must execute all safe steps in order and leave original DataFrame untouched
    orig_copy = messy_dataframe.copy(deep=True)
    cleaned_df, records = auto_clean_safe_steps(messy_dataframe)

    # Original is never modified
    pd.testing.assert_frame_equal(messy_dataframe, orig_copy)

    # Empty column dropped
    assert "EmptyCol" not in cleaned_df.columns
    # Snake case applied
    assert "gross_salary" in cleaned_df.columns or "gross_salary" in [c.lower() for c in cleaned_df.columns]
    # Placeholders cleaned
    assert (cleaned_df == "N/A").sum().sum() == 0
    # Audit log recorded
    assert len(records) > 0


def test_dataset_bundle_undo():
    meta = FileMeta(name="test.csv", size_bytes=100, rows=3, cols=2, extension=".csv")
    df1 = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    bundle = DatasetBundle(original_df=df1.copy(), working_df=df1.copy(), file_meta=meta)

    # Step 1: apply operation with push_snapshot
    bundle.push_snapshot()
    bundle.working_df["a"] = bundle.working_df["a"] * 10
    assert bundle.working_df["a"].iloc[0] == 10
    assert bundle.can_undo() is True

    # Step 2: undo
    success = bundle.undo()
    assert success is True
    assert bundle.working_df["a"].iloc[0] == 1
    assert bundle.can_undo() is False

    # Step 3: reset to original
    bundle.working_df["b"] = 999
    bundle.reset_to_original()
    assert bundle.working_df["b"].iloc[0] == 4
    pd.testing.assert_frame_equal(bundle.working_df, bundle.original_df)
