"""
File validation utilities for the ingestion module.

Handles encoding detection (chardet), delimiter detection (csv.Sniffer),
and DataFrame post-load validation (duplicate columns, unnamed headers,
empty data, single-column/row warnings).
"""

import csv
import io
import re
from typing import List, Optional, Tuple

import chardet
import pandas as pd

from core.utils.logging import get_logger, log_metadata

logger = get_logger(__name__)

MAX_FILE_SIZE_MB = 200
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json"}


def check_file_size(size_bytes: int) -> Optional[str]:
    """
    Check if file size is within the allowed limit.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Error message string if too large, None if OK.
    """
    if size_bytes > MAX_FILE_SIZE_BYTES:
        size_mb = size_bytes / (1024 * 1024)
        return (
            f"File size ({size_mb:.1f} MB) exceeds the {MAX_FILE_SIZE_MB} MB limit. "
            f"Please upload a smaller file."
        )
    return None


def check_extension(filename: str) -> Optional[str]:
    """
    Check if the file extension is supported.

    Args:
        filename: Original filename.

    Returns:
        Error message if unsupported, None if OK.
    """
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        return (
            f"Unsupported file format '{ext}'. "
            f"Supported formats: {supported}"
        )
    return None


def detect_encoding(file_bytes: bytes) -> str:
    """
    Detect the encoding of a file using chardet with fallback chain.

    Falls back to: utf-8 -> utf-8-sig -> latin-1 -> cp1252.

    Args:
        file_bytes: Raw file content.

    Returns:
        Detected encoding string.
    """
    if not file_bytes:
        return "utf-8"

    # Try chardet first
    result = chardet.detect(file_bytes[:10000])
    detected = result.get("encoding", None)
    confidence = result.get("confidence", 0)

    log_metadata(
        logger,
        "Encoding detection",
        detected=detected,
        confidence=confidence,
    )

    if detected and confidence > 0.7:
        # Normalize common aliases
        encoding = detected.lower().replace("-", "_")
        if encoding in ("ascii", "utf_8", "utf8"):
            return "utf-8"
        if encoding == "utf_8_sig":
            return "utf-8-sig"
        return detected

    # Fallback chain: try each encoding
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            file_bytes[:5000].decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"  # ultimate fallback


def detect_delimiter(text_sample: str) -> str:
    """
    Detect the CSV delimiter using csv.Sniffer.

    Args:
        text_sample: A sample of the text content.

    Returns:
        Detected delimiter character, defaults to ','.
    """
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text_sample, delimiters=",;\t|")
        detected = dialect.delimiter
        log_metadata(logger, "Delimiter detection", delimiter=repr(detected))
        return detected
    except csv.Error:
        log_metadata(logger, "Delimiter detection failed, defaulting to comma")
        return ","


def validate_dataframe(
    df: pd.DataFrame, filename: str
) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """
    Validate a loaded DataFrame and fix common issues.

    Handles:
    - Empty DataFrames (error)
    - No rows (error)
    - No columns (error)
    - Duplicate column names (auto-suffix + warning)
    - Unnamed/missing headers (generate names + warning)
    - Single-column data (warning)
    - Single-row data (warning)

    Args:
        df: The loaded DataFrame.
        filename: Original filename for error messages.

    Returns:
        Tuple of (cleaned_df, warnings, errors).
    """
    warnings: List[str] = []
    errors: List[str] = []

    if df is None:
        errors.append(f"Failed to read data from '{filename}'.")
        return pd.DataFrame(), warnings, errors

    # Check empty
    if df.empty and len(df.columns) == 0:
        errors.append(
            f"The file '{filename}' appears to be empty or contains no readable data."
        )
        return df, warnings, errors

    # Check no rows
    if len(df) == 0:
        errors.append(
            f"The file '{filename}' contains headers but no data rows."
        )
        return df, warnings, errors

    # Handle unnamed/missing headers
    unnamed_cols = [
        col for col in df.columns
        if (
            str(col).startswith("Unnamed:")
            or str(col).strip() == ""
            or re.match(r"^\d+$", str(col))
        )
    ]
    if unnamed_cols:
        new_cols = []
        unnamed_count = 0
        for col in df.columns:
            if col in unnamed_cols:
                unnamed_count += 1
                new_cols.append(f"Column_{unnamed_count}")
            else:
                new_cols.append(str(col))
        df.columns = new_cols
        warnings.append(
            f"Found {len(unnamed_cols)} unnamed or missing column header(s). "
            f"Auto-generated names: {', '.join(new_cols[:5])}{'...' if len(unnamed_cols) > 5 else ''}."
        )

    # Handle duplicate column names, including pandas auto-mangled names like "id.1"
    normalized_names = [re.sub(r"\.\d+$", "", str(col)) for col in df.columns]
    if len(set(normalized_names)) != len(normalized_names):
        dupes = sorted({name for name in normalized_names if normalized_names.count(name) > 1})
        seen: dict = {}
        new_cols = []
        for col in df.columns:
            base_name = re.sub(r"\.\d+$", "", str(col))
            if base_name in seen:
                seen[base_name] += 1
                new_cols.append(f"{base_name}_{seen[base_name]}")
            else:
                seen[base_name] = 0
                new_cols.append(base_name)
        df.columns = new_cols
        warnings.append(
            f"Found duplicate column names: {', '.join(str(d) for d in dupes[:5])}. "
            f"Suffixes were added automatically (e.g., '{dupes[0]}_1')."
        )

    # Single column warning
    if len(df.columns) == 1:
        warnings.append(
            f"The file contains only a single column ('{df.columns[0]}'). "
            f"This may indicate incorrect delimiter detection. "
            f"If your data uses a different separator, please re-upload."
        )

    # Single row warning
    if len(df) == 1:
        warnings.append(
            "The file contains only a single data row. "
            "Statistical analysis will be limited."
        )

    # Strip whitespace from column names
    df.columns = [str(col).strip() for col in df.columns]

    return df, warnings, errors
