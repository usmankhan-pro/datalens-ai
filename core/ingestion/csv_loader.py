"""
CSV file loader with encoding and delimiter auto-detection.
"""

import io
from typing import Optional

import pandas as pd

from core.ingestion.models import LoadResult
from core.ingestion.validators import (
    detect_encoding,
    detect_delimiter,
    validate_dataframe,
)
from core.utils.logging import get_logger, log_error, log_metadata

logger = get_logger(__name__)


def load_csv(
    file_content: bytes,
    filename: str,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> LoadResult:
    """
    Load a CSV file with auto-detected encoding and delimiter.

    Args:
        file_content: Raw file bytes.
        filename: Original filename.
        encoding: Force a specific encoding (auto-detect if None).
        delimiter: Force a specific delimiter (auto-detect if None).

    Returns:
        LoadResult with the loaded DataFrame or errors.
    """
    result = LoadResult(file_meta={"name": filename, "extension": ".csv"})

    try:
        # Detect encoding
        enc = encoding or detect_encoding(file_content)
        result.file_meta["encoding"] = enc

        # Decode content
        try:
            text_content = file_content.decode(enc)
        except (UnicodeDecodeError, LookupError):
            # Fallback
            for fallback_enc in ["utf-8", "latin-1", "cp1252"]:
                try:
                    text_content = file_content.decode(fallback_enc)
                    enc = fallback_enc
                    result.file_meta["encoding"] = enc
                    result.warnings.append(
                        f"Encoding detection suggested '{encoding or 'unknown'}' but "
                        f"fell back to '{fallback_enc}'."
                    )
                    break
                except UnicodeDecodeError:
                    continue
            else:
                result.errors.append(
                    f"Unable to decode the file '{filename}'. "
                    f"The file may use an unsupported character encoding."
                )
                return result

        # Detect delimiter
        delim = delimiter or detect_delimiter(text_content[:5000])
        result.file_meta["delimiter"] = delim

        # Read CSV
        df = pd.read_csv(
            io.StringIO(text_content),
            delimiter=delim,
            on_bad_lines="warn",
            engine="python",
        )

        log_metadata(
            logger,
            "CSV loaded",
            filename=filename,
            encoding=enc,
            delimiter=repr(delim),
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

    except pd.errors.EmptyDataError:
        result.errors.append(
            f"The file '{filename}' is empty or contains no parseable data."
        )
    except Exception as e:
        log_error(logger, "CSV loading failed", error=e, filename=filename)
        result.errors.append(
            f"Failed to read '{filename}' as CSV: {type(e).__name__}. "
            f"Please check that the file is a valid CSV."
        )

    return result
