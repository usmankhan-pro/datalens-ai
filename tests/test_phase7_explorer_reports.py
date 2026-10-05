import io
from zipfile import ZipFile

import pandas as pd

from core.reporting import generate_csv_report, generate_excel_report, generate_pdf_report


def test_generate_excel_report_contains_expected_sheets():
    df = pd.DataFrame({
        "Revenue": [100.0, 200.0, 150.0],
        "Region": ["North", "South", "North"],
    })

    excel_bytes = generate_excel_report(df, issues=[{"type": "missing_values", "column": "Revenue"}])

    assert isinstance(excel_bytes, (bytes, bytearray))
    with ZipFile(io.BytesIO(excel_bytes)) as workbook:
        names = set(workbook.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/worksheets/sheet1.xml" in names


def test_generate_pdf_report_creates_non_empty_output():
    df = pd.DataFrame({"Revenue": [100, 200, 300], "Cost": [50, 70, 90]})

    pdf_bytes = generate_pdf_report(df, quality_summary={"overall_score": 88.5})

    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 100


def test_generate_csv_report_preserves_dataset_data():
    df = pd.DataFrame({"Revenue": [10, 20], "Region": ["North", "South"]})

    csv_bytes = generate_csv_report(df)
    text = csv_bytes.decode("utf-8")

    assert "Revenue" in text
    assert "North" in text
    assert "South" in text
