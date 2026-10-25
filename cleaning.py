"""Copy-based dataset cleaning helpers."""

from typing import Any

import pandas as pd


def _log(step: str, column: str, rows_affected: int) -> dict[str, Any]:
    """Build one cleaning log record."""
    return {"step": step, "column": column, "rows_affected": rows_affected}


def remove_duplicates(data: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Remove duplicate rows from a copy."""
    cleaned = data.drop_duplicates().copy()
    count = len(data) - len(cleaned)
    return cleaned, [_log("Remove duplicates", "All columns", count)]


def fix_types(data: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Convert fully numeric text columns to numeric values."""
    cleaned = data.copy()
    records = []
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        converted = pd.to_numeric(cleaned[column], errors="coerce")
        valid = cleaned[column].isna() | converted.notna()
        if valid.all():
            changed = int((cleaned[column].notna() & converted.notna()).sum())
            if not pd.api.types.is_numeric_dtype(cleaned[column].dtype):
                cleaned[column] = converted
                records.append(_log("Fix types", column, changed))
    return cleaned, records


def normalize_text(data: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Strip text and unify case and the NY spelling variant."""
    cleaned = data.copy()
    records = []
    for column in cleaned.select_dtypes(include=["object", "string"]).columns:
        values = cleaned[column]
        stripped = values.map(lambda value: value.strip() if isinstance(value, str) else value)
        normalized = stripped.map(
            lambda value: "new york" if isinstance(value, str) and value.casefold() == "ny"
            else value.casefold() if isinstance(value, str) else value
        )
        canonical = {}
        for key in normalized.dropna().unique():
            if isinstance(key, str) and key == "new york":
                canonical[key] = "New York"
            else:
                matches = stripped[normalized == key]
                canonical[key] = matches.mode().iloc[0]
        result = normalized.map(canonical).astype("string")
        changed = int((values.fillna("") != result.fillna("")).sum())
        cleaned[column] = result
        if changed:
            records.append(_log("Strip and unify text", column, changed))
    return cleaned, records


def fill_missing(data: pd.DataFrame, rules: dict[str, tuple[str, str]]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Apply configured missing-value rules to a copy."""
    cleaned = data.copy()
    records = []
    for column, (method, custom) in rules.items():
        missing = cleaned[column].isna()
        count = int(missing.sum())
        if not count:
            continue
        if method == "Drop rows":
            cleaned = cleaned.loc[~missing].copy()
        elif method == "Mean":
            cleaned[column] = cleaned[column].fillna(cleaned[column].mean())
        elif method == "Median":
            cleaned[column] = cleaned[column].fillna(cleaned[column].median())
        elif method == "Mode" and not cleaned[column].mode().empty:
            cleaned[column] = cleaned[column].fillna(cleaned[column].mode().iloc[0])
        elif method == "Custom":
            value: Any = pd.to_numeric(pd.Series([custom]), errors="coerce").iloc[0]
            cleaned[column] = cleaned[column].fillna(value if pd.notna(value) else custom)
        records.append(_log(f"Missing values: {method}", column, count))
    return cleaned, records


def count_iqr_outliers(data: pd.DataFrame, column: str) -> int:
    """Count values outside a column's 1.5-IQR fences."""
    values = data[column].dropna()
    if values.empty:
        return 0
    lower = values.quantile(0.25)
    upper = values.quantile(0.75)
    spread = upper - lower
    return int(((values < lower - 1.5 * spread) | (values > upper + 1.5 * spread)).sum())


def handle_outliers(data: pd.DataFrame, rules: dict[str, str]) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Cap, remove, or ignore IQR outliers on a copy."""
    cleaned = data.copy()
    records = []
    for column, action in rules.items():
        values = cleaned[column].dropna()
        lower = values.quantile(0.25)
        upper = values.quantile(0.75)
        spread = upper - lower
        low_fence = lower - 1.5 * spread
        high_fence = upper + 1.5 * spread
        outliers = (cleaned[column] < low_fence) | (cleaned[column] > high_fence)
        count = int(outliers.sum())
        if action == "Cap":
            cleaned[column] = cleaned[column].clip(low_fence, high_fence)
        elif action == "Remove":
            cleaned = cleaned.loc[~outliers].copy()
        records.append(_log(f"IQR outliers: {action}", column, count if action != "Ignore" else 0))
    return cleaned, records


def clean_data(
    data: pd.DataFrame,
    enabled: dict[str, bool],
    missing_rules: dict[str, tuple[str, str]],
    outlier_rules: dict[str, str],
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    """Run enabled cleaning steps in the required order on copies."""
    cleaned = data.copy(deep=True)
    records: list[dict[str, Any]] = []
    steps = [("duplicates", remove_duplicates), ("types", fix_types), ("text", normalize_text)]
    for key, operation in steps:
        if enabled.get(key, False):
            cleaned, step_records = operation(cleaned)
            records.extend(step_records)
    if enabled.get("missing", False):
        cleaned, step_records = fill_missing(cleaned, missing_rules)
        records.extend(step_records)
    if enabled.get("outliers", False):
        cleaned, step_records = handle_outliers(cleaned, outlier_rules)
        records.extend(step_records)
    return cleaned, records
