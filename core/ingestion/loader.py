"""
Main file loader dispatcher for DataLens AI.

Routes uploaded files to the appropriate format-specific loader
based on file extension. Handles file size validation and
unsupported format detection.
"""

import os
from typing import Optional

from core.ingestion.models import LoadResult
from core.ingestion.csv_loader import load_csv
from core.ingestion.excel_loader import load_excel, get_sheet_names
from core.ingestion.json_loader import load_json
from core.ingestion.validators import check_file_size, check_extension
from core.utils.logging import get_logger, log_metadata, log_error, TimingContext

logger = get_logger(__name__)


def load_file(
    file_content: bytes,
    filename: str,
    sheet_name: Optional[str] = None,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> LoadResult:
    """
    Load a file into a DataFrame.

    This is the main entry point for data ingestion. It validates the
    file, determines the format from the extension, and dispatches to
    the appropriate loader.

    Args:
        file_content: Raw bytes of the uploaded file.
        filename: Original filename (used for extension detection).
        sheet_name: For Excel files, which sheet to load.
        encoding: For CSV files, force a specific encoding.
        delimiter: For CSV files, force a specific delimiter.

    Returns:
        LoadResult with the loaded DataFrame, warnings, errors, and metadata.
    """
    result = LoadResult(file_meta={"name": filename})

    # Check file size
    size_error = check_file_size(len(file_content))
    if size_error:
        result.errors.append(size_error)
        return result

    # Check extension
    ext_error = check_extension(filename)
    if ext_error:
        result.errors.append(ext_error)
        return result

    # Check empty content
    if not file_content or len(file_content) == 0:
        result.errors.append(
            f"The file '{filename}' is empty (0 bytes). "
            f"Please upload a file with data."
        )
        return result

    ext = os.path.splitext(filename)[1].lower()

    with TimingContext(logger, f"Loading {filename}"):
        try:
            if ext == ".csv":
                result = load_csv(
                    file_content, filename,
                    encoding=encoding, delimiter=delimiter,
                )
            elif ext in (".xlsx", ".xls"):
                result = load_excel(
                    file_content, filename,
                    sheet_name=sheet_name,
                )
            elif ext == ".json":
                result = load_json(file_content, filename)
            else:
                result.errors.append(
                    f"Unsupported file format '{ext}'."
                )
        except Exception as e:
            log_error(logger, "Unexpected loading error", error=e, filename=filename)
            result.errors.append(
                f"An unexpected error occurred while loading '{filename}': "
                f"{type(e).__name__}. Please try again or use a different file."
            )

    if result.success:
        log_metadata(
            logger,
            "File loaded successfully",
            filename=filename,
            rows=result.file_meta.get("rows"),
            cols=result.file_meta.get("cols"),
        )

    return result
