"""
JSON file loader with support for nested structures via json_normalize.
"""

import io
import json
from typing import Optional

import pandas as pd

from core.ingestion.models import LoadResult
from core.ingestion.validators import validate_dataframe
from core.utils.logging import get_logger, log_error, log_metadata

logger = get_logger(__name__)


def load_json(
    file_content: bytes,
    filename: str,
) -> LoadResult:
    """
    Load a JSON file. Supports:
    - Array of flat objects -> DataFrame directly
    - Array of nested objects -> json_normalize flattening
    - Single nested object -> json_normalize

    Args:
        file_content: Raw file bytes.
        filename: Original filename.

    Returns:
        LoadResult with the loaded DataFrame or errors.
    """
    result = LoadResult(file_meta={"name": filename, "extension": ".json"})

    try:
        # Decode
        text = file_content.decode("utf-8")
        data = json.loads(text)

        df: Optional[pd.DataFrame] = None

        if isinstance(data, list):
            if len(data) == 0:
                result.errors.append(
                    f"The JSON file '{filename}' contains an empty array."
                )
                return result

            # Try json_normalize for nested structures
            try:
                df = pd.json_normalize(data, max_level=3)
                if any("." in str(col) for col in df.columns):
                    result.warnings.append(
                        "Nested JSON structure detected. "
                        "Columns have been flattened with '.' separators."
                    )
            except Exception:
                # Fall back to simple DataFrame
                df = pd.DataFrame(data)

        elif isinstance(data, dict):
            # Single object or dict with array values
            # Check if any value is a list (tabular data)
            list_vals = {k: v for k, v in data.items() if isinstance(v, list)}
            if list_vals:
                # Try the first list key
                key = max(list_vals, key=lambda k: len(list_vals[k]))
                try:
                    df = pd.json_normalize(list_vals[key], max_level=3)
                    result.warnings.append(
                        f"Loaded data from the '{key}' key in the JSON object. "
                        f"The JSON structure was automatically flattened."
                    )
                except Exception:
                    df = pd.DataFrame(list_vals[key])
            else:
                # Single flat object -> single-row DataFrame
                try:
                    df = pd.json_normalize(data, max_level=3)
                except Exception:
                    df = pd.DataFrame([data])
                result.warnings.append(
                    "The JSON file contains a single object. "
                    "Converted to a single-row DataFrame."
                )
        else:
            result.errors.append(
                f"Unsupported JSON structure in '{filename}'. "
                f"Expected an array of objects or a JSON object."
            )
            return result

        if df is not None:
            log_metadata(
                logger,
                "JSON loaded",
                filename=filename,
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

    except json.JSONDecodeError as e:
        result.errors.append(
            f"The file '{filename}' is not valid JSON: {e.msg} "
            f"(line {e.lineno}, column {e.colno}). "
            f"Please check the file format."
        )
    except UnicodeDecodeError:
        result.errors.append(
            f"The file '{filename}' contains invalid characters. "
            f"JSON files must be UTF-8 encoded."
        )
    except Exception as e:
        log_error(logger, "JSON loading failed", error=e, filename=filename)
        result.errors.append(
            f"Failed to read '{filename}' as JSON: {type(e).__name__}. "
            f"Please check that the file is valid JSON."
        )

    return result
