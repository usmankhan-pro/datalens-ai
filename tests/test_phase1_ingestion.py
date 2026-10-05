import json

import pandas as pd

from core.ingestion.loader import load_file
from data.demo.generator import generate_demo_dataset, save_ground_truth


def test_semicolon_delimited_csv_loads():
    path = "tests/fixtures/semicolon_delimited.csv"
    with open(path, "rb") as fh:
        payload = fh.read()

    result = load_file(payload, "semicolon_delimited.csv")

    assert result.success is True
    assert result.df is not None
    assert list(result.df.columns) == ["name", "age", "city"]
    assert result.df.shape[0] > 0


def test_duplicate_column_names_are_suffixed_and_warned():
    df = pd.DataFrame([[1, 2], [3, 4]], columns=["id", "id"])
    payload = df.to_csv(index=False).encode("utf-8")

    result = load_file(payload, "duplicate_columns.csv")

    assert result.success is True
    assert result.df.columns.tolist() == ["id", "id_1"]
    assert any("duplicate column" in warning.lower() for warning in result.warnings)


def test_nested_json_is_flattened():
    payload = b'{"records": [{"user": {"name": "Ada"}, "score": 10}, {"user": {"name": "Lin"}, "score": 20}]}'

    result = load_file(payload, "nested.json")

    assert result.success is True
    assert result.df is not None
    assert "user.name" in result.df.columns
    assert result.df.shape[0] == 2


def test_unsupported_extension_returns_error():
    result = load_file(b"abc", "badfile.unsupported")

    assert result.success is False
    assert any("Unsupported file format" in e for e in result.errors)


def test_demo_dataset_matches_ground_truth_file():
    df, gt = generate_demo_dataset()
    ground_truth_path = save_ground_truth(gt)

    with open(ground_truth_path, "r", encoding="utf-8") as fh:
        saved = json.load(fh)

    assert df.shape[0] == 5000 + gt["duplicate_rows"]
    assert saved["duplicate_rows"] == gt["duplicate_rows"]
    assert saved["negative_quantities"] == gt["negative_quantities"]
    assert saved["unparseable_dates"] == gt["unparseable_dates"]
    assert saved["missing_marketing_spend"] == gt["missing_marketing_spend"]
    assert saved["revenue_outliers"] == gt["revenue_outliers"]
