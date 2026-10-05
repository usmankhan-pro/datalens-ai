"""
Excel file loader with multi-sheet support (.xlsx, .xls).
"""

import io
from typing import List, Optional

import pandas as pd

from core.ingestion.models import LoadResult
from core.ingestion.validators import validate_dataframe
from core.utils.logging import get_logger, log_error, log_metadata

logger = get_logger(__name__)


def get_sheet_names(file_content: bytes, filename: str) -> List[str]:
    """
    Get the list of sheet names from an Excel file.

    Args:
        file_content: Raw file bytes.
        filename: Original filename.

    Returns:
        List of sheet names. Empty list on error.
    """
    try:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        engine = "xlrd" if ext == "xls" else "openpyxl"
        xls = pd.ExcelFile(io.BytesIO(file_content), engine=engine)
        return xls.sheet_names
    except Exception as e:
        log_error(logger, "Failed to read sheet names", error=e, filename=filename)
        return []


def load_excel(
    file_content: bytes,
    filename: str,
    sheet_name: Optional[str] = None,
) -> LoadResult:
    """
    Load an Excel file (.xlsx or .xls).

    Args:
        file_content: Raw file bytes.
        filename: Original filename.
        sheet_name: Specific sheet to load. Loads first sheet if None.

    Returns:
        LoadResult with the loaded DataFrame or errors.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    result = LoadResult(file_meta={"name": filename, "extension": f".{ext}"})

    try:
        engine = "xlrd" if ext == "xls" else "openpyxl"

        # Get sheet names
        sheets = get_sheet_names(file_content, filename)
        if not sheets:
            result.errors.append(
                f"Could not read any sheets from '{filename}'. "
                f"The file may be corrupted or not a valid Excel file."
            )
            return result

        result.file_meta["sheets"] = sheets

        # Determine which sheet to load
        target_sheet = sheet_name if sheet_name and sheet_name in sheets else sheets[0]
        result.file_meta["sheet_name"] = target_sheet

        if sheet_name and sheet_name not in sheets:
            result.warnings.append(
                f"Sheet '{sheet_name}' not found. Loading '{target_sheet}' instead. "
                f"Available sheets: {', '.join(sheets)}."
            )

        if len(sheets) > 1 and sheet_name is None:
            result.warnings.append(
                f"This Excel file contains {len(sheets)} sheets: {', '.join(sheets)}. "
                f"Loading the first sheet ('{target_sheet}'). "
                f"Use the sheet selector to choose a different sheet."
            )

        # Read the sheet
        df = pd.read_excel(
            io.BytesIO(file_content),
            sheet_name=target_sheet,
            engine=engine,
        )

        log_metadata(
            logger,
            "Excel loaded",
            filename=filename,
            sheet=target_sheet,
            shape=df.shape,
        )

        # Validate
        df, warnings, errors = validate_dataframe(df, filename)
        result.warnings.extend(warnings)
        result.errors.extend(errors)

        if not errors:
            result.df = df
            result.file_meta["rows"] = len(df)
            result.file_meta["cols"] = len(df.columns)
            result.file_meta["size_bytes"] = len(file_content)

    except Exception as e:
        log_error(logger, "Excel loading failed", error=e, filename=filename)
        result.errors.append(
            f"Failed to read '{filename}' as Excel: {type(e).__name__}. "
            f"The file may be corrupted or in an unsupported format."
        )

    return result
