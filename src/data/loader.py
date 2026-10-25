"""In-memory CSV and Excel loading with explicit format validation."""

from __future__ import annotations

import csv
from collections import Counter
from io import BytesIO, StringIO, TextIOWrapper
from pathlib import Path
from typing import BinaryIO, Any

import pandas as pd

from config.settings import RESOURCE_LIMITS

_CSV_DELIMITERS = ",;\t|"
_ENCODINGS = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


def _read_bytes(source: bytes | bytearray | BinaryIO) -> bytes:
    if isinstance(source, (bytes, bytearray)):
        return bytes(source)
    if hasattr(source, "seek"):
        source.seek(0)
    return source.read()


def _detect_delimiter(content: bytes, encoding: str) -> str:
    sample = content[:65536].decode(encoding, errors="ignore")
    best_delimiter = ","
    best_score = (0, 0, 0.0)
    for candidate in _CSV_DELIMITERS:
        rows = [
            row
            for row in csv.reader(StringIO(sample), delimiter=candidate)
            if row and any(cell.strip() for cell in row)
        ]
        widths = [len(row) for row in rows]
        multi_column_rows = sum(width > 1 for width in widths)
        if multi_column_rows == 0:
            continue
        modal_width, modal_count = Counter(widths).most_common(1)[0]
        score = (
            multi_column_rows,
            modal_count,
            modal_width / max(len(widths), 1),
        )
        if score > best_score:
            best_delimiter = candidate
            best_score = score
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters=_CSV_DELIMITERS).delimiter
    except csv.Error:
        return best_delimiter
    return best_delimiter if best_score[0] else sniffed


def _validate_csv_widths(content: bytes, encoding: str, delimiter: str) -> None:
    reader = csv.reader(
        TextIOWrapper(BytesIO(content), encoding=encoding, newline=""),
        delimiter=delimiter,
    )
    header_width: int | None = None
    for row in reader:
        if not row or not any(cell.strip() for cell in row):
            continue
        if header_width is None:
            header_width = len(row)
        elif len(row) > header_width:
            raise ValueError(
                f"CSV record ending on line {reader.line_num} contains "
                "more fields than its header. Check the delimiter or repair "
                "the malformed row."
            )


def excel_sheet_names(source: bytes | bytearray | BinaryIO) -> list[str]:
    """Return workbook sheet names without loading a sheet into a DataFrame."""
    content = _read_bytes(source)
    _validate_file_size(content)
    try:
        with pd.ExcelFile(BytesIO(content), engine="openpyxl") as workbook:
            return workbook.sheet_names
    except (OSError, ValueError, ImportError) as error:
        raise ValueError(f"Unable to read Excel workbook: {error}") from error


def _validate_file_size(content: bytes) -> None:
    max_bytes = RESOURCE_LIMITS.max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ValueError(
            f"File is {len(content) / (1024 * 1024):.1f} MB; "
            f"the limit is {RESOURCE_LIMITS.max_file_size_mb} MB."
        )
    if not content:
        raise ValueError("The uploaded file is empty.")


def _normalize_blank_cells(data: pd.DataFrame) -> pd.DataFrame:
    return data.replace(r"^\s*$", pd.NA, regex=True)


def load_table(
    source: bytes | bytearray | BinaryIO,
    filename: str,
    *,
    delimiter: str = "auto",
    encoding: str = "auto",
    sheet_name: str | int = 0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load CSV or Excel bytes and return the table plus observed metadata."""
    content = _read_bytes(source)
    _validate_file_size(content)
    extension = Path(filename).suffix.casefold()
    metadata: dict[str, Any] = {
        "filename": Path(filename).name,
        "file_size_bytes": len(content),
        "format": extension.lstrip(".").upper(),
        "delimiter": None,
        "encoding": None,
        "sheet_name": None,
    }

    if extension == ".csv":
        if delimiter != "auto" and delimiter not in _CSV_DELIMITERS:
            raise ValueError("Choose a supported delimiter: comma, semicolon, tab, or pipe.")

        selected_encoding = encoding
        if encoding == "auto":
            selected_encoding = next(
                (candidate for candidate in _ENCODINGS if _decodes(content, candidate)),
                "utf-8",
            )
        elif not _decodes(content, encoding):
            raise ValueError(f"The CSV cannot be decoded using {encoding}.")

        selected_delimiter = (
            _detect_delimiter(content, selected_encoding)
            if delimiter == "auto"
            else delimiter
        )
        metadata.update(encoding=selected_encoding, delimiter=selected_delimiter)
        try:
            _validate_csv_widths(content, selected_encoding, selected_delimiter)
            data = pd.read_csv(
                BytesIO(content),
                sep=selected_delimiter,
                encoding=selected_encoding,
                dtype={"TotalCharges": str},
                skipinitialspace=True,
                on_bad_lines="error",
            )
        except pd.errors.EmptyDataError as error:
            raise ValueError("The uploaded CSV has no header or data.") from error
        except (pd.errors.ParserError, UnicodeError, LookupError) as error:
            raise ValueError(f"Unable to parse CSV: {error}") from error
    elif extension in {".xlsx", ".xlsm"}:
        try:
            data = pd.read_excel(
                BytesIO(content),
                sheet_name=sheet_name,
                dtype={"TotalCharges": str},
                engine="openpyxl",
            )
        except (ValueError, OSError, ImportError) as error:
            raise ValueError(f"Unable to read Excel worksheet: {error}") from error
        metadata["sheet_name"] = str(sheet_name)
    else:
        raise ValueError("Choose a CSV, XLSX, or XLSM file.")

    if len(data) > RESOURCE_LIMITS.max_rows:
        raise ValueError(
            f"The file contains {len(data):,} rows; the limit is "
            f"{RESOURCE_LIMITS.max_rows:,} rows."
        )

    data = _normalize_blank_cells(data)
    metadata.update(rows=len(data), columns=len(data.columns))
    return data, metadata


def _decodes(content: bytes, encoding: str) -> bool:
    try:
        content.decode(encoding)
    except (UnicodeError, LookupError):
        return False
    return True
