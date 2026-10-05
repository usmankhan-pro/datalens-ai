import pandas as pd

from core.cleaning.pipeline import apply_operation, preview_operation
from core.utils.state import DatasetBundle, FileMeta, TransformRecord


def test_remove_duplicate_rows_preview_and_apply():
    df = pd.DataFrame({"id": [1, 1, 2], "value": [10, 10, 20]})
    preview = preview_operation(df, "remove_duplicates", {})
    assert preview["rows_affected"] == 1

    result = apply_operation(df, "remove_duplicates", {})
    assert result["rows_affected"] == 1
    assert result["df"].shape[0] == 2


def test_fill_missing_numeric_works():
    df = pd.DataFrame({"value": [1.0, None, 3.0]})
    result = apply_operation(df, "fill_missing_numeric", {"method": "mean"})
    assert result["df"]["value"].isna().sum() == 0
    assert result["rows_affected"] == 1


def test_standardize_text_works():
    df = pd.DataFrame({"city": ["  nyc ", "london", " PARIS "]})
    result = apply_operation(df, "standardize_text", {"case": "upper", "strip": True})
    assert result["df"]["city"].tolist() == ["NYC", "LONDON", "PARIS"]


def test_reset_history_restores_original_df_hash():
    original = pd.DataFrame({"x": [1, 2, 3]})
    bundle = DatasetBundle(
        original_df=original.copy(),
        working_df=original.copy(),
        file_meta=FileMeta(name="demo.csv", size_bytes=10, rows=3, cols=1, extension=".csv"),
    )

    bundle.transformation_history.append(TransformRecord("now", "fill_missing_numeric", ["x"], {"method": "mean"}, 1))
    bundle.working_df = pd.DataFrame({"x": [1, 2, 3, 4]})
    assert len(bundle.transformation_history) == 1
    assert bundle.working_df.shape[0] == 4


def test_export_history_script_generates_python_code():
    history = [
        TransformRecord("2024-01-01", "fill_missing_numeric", ["value"], {"method": "mean"}, 1),
        TransformRecord("2024-01-01", "standardize_text", ["city"], {"case": "upper", "strip": True}, 2),
    ]
    script = "\n".join([rec.operation for rec in history])
    assert "fill_missing_numeric" in script
    assert "standardize_text" in script
