"""Unit tests for Stage 6: Cleaning Recipes and 5 Sample Datasets Ingestion."""

import os
import json
import pandas as pd
import pytest

from core.ingestion import load_file
from core.recipes import (
    CleaningRecipe,
    apply_recipe,
    load_recipe,
    save_recipe,
    validate_recipe_compatibility,
)
from core.utils.state import TransformRecord


def test_save_and_load_recipe():
    history = [
        TransformRecord(
            timestamp="2023-01-01 10:00:00",
            operation="snake_case_columns",
            columns=[],
            params={},
            rows_affected=0,
            stage="structure",
            risk="safe",
        ),
        TransformRecord(
            timestamp="2023-01-01 10:01:00",
            operation="remove_duplicates",
            columns=["id", "name"],
            params={"keep": "first"},
            rows_affected=1,
            stage="duplicates",
            risk="safe",
        ),
    ]

    json_str = save_recipe(history, name="test_recipe", description="A test pipeline")
    assert isinstance(json_str, str)

    parsed = json.loads(json_str)
    assert parsed["name"] == "test_recipe"
    assert len(parsed["steps"]) == 2

    loaded = load_recipe(json_str)
    assert isinstance(loaded, CleaningRecipe)
    assert loaded.name == "test_recipe"
    assert len(loaded.steps) == 2


def test_recipe_compatibility_and_apply():
    df = pd.DataFrame({
        "User Name": [" Alice ", "Bob", "Bob"],
        "User Age": [25, 30, 30],
    })

    recipe = CleaningRecipe(
        name="user_clean_recipe",
        created_at="2023-01-01",
        description="Clean users",
        target_columns=["User Name", "User Age"],
        steps=[
            {
                "step": 1,
                "operation": "snake_case_columns",
                "stage": "structure",
                "risk": "safe",
                "columns": [],
                "params": {},
            },
            {
                "step": 2,
                "operation": "remove_duplicates",
                "stage": "duplicates",
                "risk": "safe",
                "columns": [],
                "params": {"keep": "first"},
            },
        ],
    )

    compat, warns = validate_recipe_compatibility(recipe, df)
    assert compat is True

    orig_copy = df.copy()
    cleaned_df, records, app_warns = apply_recipe(df, recipe)

    # Original unchanged
    pd.testing.assert_frame_equal(df, orig_copy)

    # Columns became snake_case and duplicates removed
    assert "user_name" in cleaned_df.columns
    assert len(cleaned_df) == 2
    assert len(records) == 2


@pytest.mark.parametrize("filename", [
    "sample_ecommerce_dirty.csv",
    "sample_churn_ml.csv",
    "sample_financial_reporting.xlsx",
    "sample_patient_research.csv",
    "sample_marketing_leads.json",
])
def test_sample_datasets_ingestion(filename):
    filepath = os.path.join("data", filename)
    assert os.path.exists(filepath), f"Sample file {filepath} not found!"

    with open(filepath, "rb") as f:
        content = f.read()

    res = load_file(content, filename)
    assert res.success is True, f"Failed loading {filename}: {res.errors}"
    assert res.df is not None
    assert len(res.df) > 0
    assert len(res.df.columns) > 0
