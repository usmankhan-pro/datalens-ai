"""Python / pandas script generator for DataLens AI.

Generates reproducible, standalone Python scripts that replicate all cleaning
operations applied during the session. The generated script can be executed
independently of DataLens AI.
"""

from __future__ import annotations

import json
from typing import Any, List, Sequence


def generate_cleaning_script(
    history: Sequence[Any],
    input_filename: str = "dataset.csv",
    output_filename: str = "cleaned_dataset.csv",
) -> str:
    """
    Generate an executable Python script reproducing the cleaning pipeline.

    Args:
        history: Sequence of TransformRecord objects or dictionaries with operation info.
        input_filename: Path to the input dataset file.
        output_filename: Path where the cleaned dataset should be saved.

    Returns:
        String containing the Python script.
    """
    lines: List[str] = [
        '#!/usr/bin/env python3',
        '"""',
        'DataLens AI - Automated Cleaning Pipeline Script',
        'Generated reproducible script to clean raw dataset.',
        '"""',
        '',
        'import re',
        'import numpy as np',
        'import pandas as pd',
        '',
        '',
        'def clean_dataset(input_path: str, output_path: str) -> pd.DataFrame:',
        '    """Load raw data, apply transformations sequentially, and save cleaned data."""',
        f'    print(f"Loading raw data from {{input_path}}...")',
        '    # Handle various extensions dynamically',
        '    if input_path.endswith((".xlsx", ".xls")):',
        '        df = pd.read_excel(input_path)',
        '    elif input_path.endswith(".json"):',
        '        df = pd.read_json(input_path)',
        '    else:',
        '        df = pd.read_csv(input_path)',
        '',
        '    initial_rows, initial_cols = df.shape',
        '    print(f"Initial shape: {initial_rows:,} rows x {initial_cols} columns")',
        '',
    ]

    if not history:
        lines.append('    # No cleaning operations were applied')
        lines.append('    print("No transformations recorded.")')
    else:
        for idx, item in enumerate(history, start=1):
            op = getattr(item, "operation", None) or (item.get("operation") if isinstance(item, dict) else str(item))
            params = getattr(item, "params", None) or (item.get("params") if isinstance(item, dict) else {})
            rows_aff = getattr(item, "rows_affected", None) or (item.get("rows_affected") if isinstance(item, dict) else 0)
            cols = getattr(item, "columns", None) or (item.get("columns") if isinstance(item, dict) else [])

            lines.append(f'    # Step {idx}: {op}')
            lines.append(f'    # Expected affected rows/cells: {rows_aff}')

            if op == "drop_duplicates" or op == "remove_duplicates":
                subset = params.get("subset")
                keep = params.get("keep", "first")
                if subset:
                    lines.append(f'    df = df.drop_duplicates(subset={subset!r}, keep={keep!r}).copy()')
                else:
                    lines.append(f'    df = df.drop_duplicates(keep={keep!r}).copy()')

            elif op == "drop_empty_rows":
                how = params.get("how", "all")
                lines.append(f'    df = df.dropna(how={how!r}).copy()')

            elif op == "drop_empty_columns":
                lines.append('    df = df.dropna(axis=1, how="all").copy()')

            elif op == "snake_case_columns":
                lines.append('    def _to_snake_case(name: str) -> str:')
                lines.append('        s = re.sub(r"[\\s\\-\\.]+", "_", str(name).strip())')
                lines.append('        s = re.sub(r"[^\\w]", "", s)')
                lines.append('        s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\\1_\\2", s)')
                lines.append('        s = re.sub(r"([a-z\\d])([A-Z])", r"\\1_\\2", s)')
                lines.append('        return s.lower()')
                lines.append('    df.columns = [_to_snake_case(c) for c in df.columns]')

            elif op == "replace_placeholders" or op == "clean_invalid_placeholders":
                placeholders = params.get("placeholders", ["N/A", "NA", "-", "none", "null", "999", "-999", "?", ""])
                target_cols = params.get("columns", cols or list(params.get("columns", [])))
                lines.append(f'    placeholders = {placeholders!r}')
                if target_cols:
                    lines.append(f'    for col in {target_cols!r}:')
                    lines.append('        if col in df.columns:')
                    lines.append('            df[col] = df[col].replace(placeholders, np.nan)')
                else:
                    lines.append('    df = df.replace(placeholders, np.nan)')

            elif op == "convert_numeric_text":
                target_cols = params.get("columns", cols)
                lines.append(f'    for col in {target_cols!r}:')
                lines.append('        if col in df.columns:')
                lines.append('            df[col] = (')
                lines.append('                df[col].astype(str)')
                lines.append('                .str.replace(r"[\\$,%]", "", regex=True)')
                lines.append('                .str.replace("(", "-", regex=False)')
                lines.append('                .str.replace(")", "", regex=False)')
                lines.append('                .str.strip()')
                lines.append('            )')
                lines.append('            df[col] = pd.to_numeric(df[col], errors="coerce")')

            elif op == "parse_dates":
                target_cols = params.get("columns", cols)
                lines.append(f'    for col in {target_cols!r}:')
                lines.append('        if col in df.columns:')
                lines.append('            df[col] = pd.to_datetime(df[col], errors="coerce")')

            elif op == "convert_booleans":
                target_cols = params.get("columns", cols)
                lines.append('    bool_map = {"true": True, "1": True, "yes": True, "y": True, "t": True,')
                lines.append('                "false": False, "0": False, "no": False, "n": False, "f": False}')
                lines.append(f'    for col in {target_cols!r}:')
                lines.append('        if col in df.columns:')
                lines.append('            df[col] = df[col].astype(str).str.strip().str.lower().map(bool_map)')

            elif op == "standardize_text":
                case = params.get("case", "lower")
                strip = params.get("strip", True)
                target_cols = params.get("columns", cols)
                lines.append(f'    text_cols = {target_cols!r} if {bool(target_cols)} else df.select_dtypes(include=["object", "string"]).columns.tolist()')
                lines.append('    for col in text_cols:')
                lines.append('        if col in df.columns:')
                code = 'df[col].astype(str)'
                if strip:
                    code += '.str.strip()'
                if case == "lower":
                    code += '.str.lower()'
                elif case == "upper":
                    code += '.str.upper()'
                elif case == "title":
                    code += '.str.title()'
                lines.append(f'            df[col] = {code}')

            elif op == "fill_missing_numeric":
                method = params.get("method", "median")
                target_cols = params.get("columns", cols)
                lines.append(f'    num_cols = {target_cols!r} if {bool(target_cols)} else df.select_dtypes(include=[np.number]).columns.tolist()')
                lines.append('    for col in num_cols:')
                lines.append('        if col in df.columns:')
                if method == "mean":
                    lines.append('            val = df[col].mean()')
                elif method == "median":
                    lines.append('            val = df[col].median()')
                elif method == "mode":
                    lines.append('            val = df[col].mode().iloc[0] if not df[col].mode().empty else 0')
                elif method == "zero":
                    lines.append('            val = 0')
                else:
                    const_val = params.get("value", 0)
                    lines.append(f'            val = {const_val!r}')
                lines.append('            df[col] = df[col].fillna(val)')

            elif op == "fill_missing_categorical":
                method = params.get("method", "mode")
                target_cols = params.get("columns", cols)
                lines.append(f'    cat_cols = {target_cols!r} if {bool(target_cols)} else df.select_dtypes(include=["object", "string", "category"]).columns.tolist()')
                lines.append('    for col in cat_cols:')
                lines.append('        if col in df.columns:')
                if method == "mode":
                    lines.append('            val = df[col].mode().iloc[0] if not df[col].mode().empty else "Unknown"')
                else:
                    const_val = params.get("value", "Missing")
                    lines.append(f'            val = {const_val!r}')
                lines.append('            df[col] = df[col].fillna(val)')

            elif op == "drop_missing_rows":
                thresh_pct = params.get("threshold_pct")
                target_cols = params.get("columns", cols)
                if target_cols:
                    lines.append(f'    df = df.dropna(subset={target_cols!r}).copy()')
                elif thresh_pct is not None:
                    min_non_null = f'int(len(df.columns) * (1 - {thresh_pct / 100.0}))'
                    lines.append(f'    df = df.dropna(thresh={min_non_null}).copy()')
                else:
                    lines.append('    df = df.dropna().copy()')

            elif op == "drop_missing_columns":
                threshold = params.get("threshold", 0.5)
                lines.append(f'    max_missing = {threshold}')
                lines.append('    drop_cols = [c for c in df.columns if df[c].isna().mean() > max_missing]')
                lines.append('    if drop_cols:')
                lines.append('        df = df.drop(columns=drop_cols).copy()')

            elif op == "cap_outliers":
                method = params.get("method", "iqr")
                factor = params.get("factor", 1.5)
                target_cols = params.get("columns", cols)
                lines.append(f'    outlier_cols = {target_cols!r} if {bool(target_cols)} else df.select_dtypes(include=[np.number]).columns.tolist()')
                lines.append('    for col in outlier_cols:')
                lines.append('        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):')
                if method == "iqr":
                    lines.append('            q25 = df[col].quantile(0.25)')
                    lines.append('            q75 = df[col].quantile(0.75)')
                    lines.append('            iqr = q75 - q25')
                    lines.append(f'            lower = q25 - ({factor} * iqr)')
                    lines.append(f'            upper = q75 + ({factor} * iqr)')
                    lines.append('            df[col] = df[col].clip(lower=lower, upper=upper)')
                else:
                    lines.append('            mean = df[col].mean()')
                    lines.append('            std = df[col].std()')
                    lines.append(f'            lower = mean - ({factor} * std)')
                    lines.append(f'            upper = mean + ({factor} * std)')
                    lines.append('            df[col] = df[col].clip(lower=lower, upper=upper)')

            elif op == "remove_outliers":
                factor = params.get("factor", 1.5)
                target_cols = params.get("columns", cols)
                lines.append(f'    outlier_cols = {target_cols!r} if {bool(target_cols)} else df.select_dtypes(include=[np.number]).columns.tolist()')
                lines.append('    for col in outlier_cols:')
                lines.append('        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):')
                lines.append('            q25 = df[col].quantile(0.25)')
                lines.append('            q75 = df[col].quantile(0.75)')
                lines.append('            iqr = q75 - q25')
                lines.append(f'            lower = q25 - ({factor} * iqr)')
                lines.append(f'            upper = q75 + ({factor} * iqr)')
                lines.append('            df = df[(df[col] >= lower) & (df[col] <= upper) | df[col].isna()].copy()')

            else:
                lines.append(f'    # Custom or unknown operation: {op}')
                lines.append(f'    # params: {json.dumps(params)}')

            lines.append('')

    lines.extend([
        '    final_rows, final_cols = df.shape',
        '    print(f"Final shape: {final_rows:,} rows x {final_cols} columns")',
        '    print(f"Exporting cleaned data to {output_path}...")',
        '    if output_path.endswith((".xlsx", ".xls")):',
        '        df.to_excel(output_path, index=False)',
        '    elif output_path.endswith(".json"):',
        '        df.to_json(output_path, orient="records", indent=2)',
        '    else:',
        '        df.to_csv(output_path, index=False)',
        '    print("Done!")',
        '    return df',
        '',
        '',
        'if __name__ == "__main__":',
        f'    clean_dataset({input_filename!r}, {output_filename!r})',
        '',
    ])

    return '\n'.join(lines)
