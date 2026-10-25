from io import BytesIO

import pandas as pd
import pytest

from src.data.loader import excel_sheet_names, load_table
from src.cleaning.audit import CleaningRecord
from src.cleaning.cleaning_pipeline import CleaningPipeline
from src.cleaning.data_types import convert_types


def test_csv_delimiter_is_detected_and_metadata_returned():
    data, metadata = load_table(
        "name;amount\nCafé;4\n".encode("utf-8"),
        "data.csv",
    )

    assert data.to_dict("records") == [{"name": "Café", "amount": 4}]
    assert metadata["delimiter"] == ";"
    assert metadata["encoding"] == "utf-8-sig"


@pytest.mark.parametrize("delimiter", [",", ";", "\t", "|"])
def test_csv_loader_detects_supported_delimiters(delimiter):
    content = f"name{delimiter}amount\nCafé{delimiter}4\n".encode("utf-8")

    data, metadata = load_table(content, "data.csv")

    assert data.to_dict("records") == [{"name": "Café", "amount": 4}]
    assert metadata["delimiter"] == delimiter


def test_single_column_csv_does_not_gain_inferred_columns():
    content = "Subscribers gained\n" + "48\n" * 365

    data, metadata = load_table(content.encode(), "subs.csv")

    assert data.shape == (365, 1)
    assert data.columns.tolist() == ["Subscribers gained"]
    assert metadata["delimiter"] == ","


def test_csv_falls_back_to_windows_encoding():
    data, metadata = load_table("city\nMontréal\n".encode("cp1252"), "cities.csv")

    assert data.loc[0, "city"] == "Montréal"
    assert metadata["encoding"] == "cp1252"


def test_delimiter_detection_tolerates_a_multibyte_character_at_sample_boundary():
    content = b"name\n" + b"a" * (65536 - 6) + "é\n".encode("utf-8")

    data, _ = load_table(content, "large-text.csv")

    assert data.shape == (1, 1)
    assert data.iloc[0, 0].endswith("é")


def test_excel_sheet_can_be_selected():
    workbook = BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame({"first": [1]}).to_excel(writer, index=False, sheet_name="First")
        pd.DataFrame({"second": [2]}).to_excel(writer, index=False, sheet_name="Second")
    content = workbook.getvalue()

    assert excel_sheet_names(content) == ["First", "Second"]
    data, metadata = load_table(content, "data.xlsx", sheet_name="Second")

    assert data.to_dict("records") == [{"second": 2}]
    assert metadata["sheet_name"] == "Second"


def test_invalid_or_empty_uploads_have_clear_errors():
    with pytest.raises(ValueError, match="empty"):
        load_table(b"", "empty.csv")
    with pytest.raises(ValueError, match="supported delimiter"):
        load_table(b"a,b\n1,2\n", "data.csv", delimiter=":")
    with pytest.raises(ValueError, match="CSV, XLSX, or XLSM"):
        load_table(b"data", "data.json")
    with pytest.raises(ValueError, match="more fields than its header"):
        load_table(b"a;b\n1;2;3\n", "malformed.csv")


def test_pipeline_preview_commit_undo_and_source_immutability():
    source = pd.DataFrame({"score": [1, 2, 2]})
    before = source.copy(deep=True)
    pipeline = CleaningPipeline(source)
    candidate = source.drop_duplicates().copy()
    record = CleaningRecord(
        step="Remove duplicates",
        column="score",
        operation="remove",
        rows_affected=1,
    )

    pipeline.apply_preview(candidate, [record])

    assert pipeline.working.shape == (2, 1)
    assert pipeline.to_result().source_immutable
    assert source.equals(before)
    assert pipeline.undo()
    assert pipeline.working.equals(before)
    assert pipeline.records == []


def test_undo_removes_all_audit_records_for_the_last_operation():
    pipeline = CleaningPipeline(pd.DataFrame({"value": [1, 1]}))
    pipeline.remove_duplicates()
    pipeline.fix_types({"value": "string"})

    assert len(pipeline.records) == 2
    assert pipeline.undo()
    assert len(pipeline.records) == 1
    assert pipeline.undo()
    assert pipeline.records == []


def test_type_conversion_counts_invalid_values_and_converts_valid_values():
    source = pd.DataFrame({"amount": ["12", "not a number", None]})

    converted, records = convert_types(source, {"amount": "numeric"})

    assert converted["amount"].iloc[0] == 12
    assert pd.isna(converted["amount"].iloc[1])
    assert records[0].parameters["n_invalid"] == 1
    assert records[0].succeeded
