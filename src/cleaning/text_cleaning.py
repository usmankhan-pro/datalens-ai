"""Text cleaning operations with preview and validation."""

from __future__ import annotations

import pandas as pd

from src.cleaning.audit import CleaningRecord


def detect_text_issues(data: pd.DataFrame) -> dict[str, dict[str, object]]:
    """Detect common text-quality issues per column.

    Issues: leading/trailing whitespace, repeated spaces, mixed case,
    blank strings, inconsistent category labels.
    """
    report: dict[str, dict[str, object]] = {}
    for col in data.columns:
        series = data[col]
        if series.dtype != object and not str(series.dtype).startswith("string"):
            continue
        non_null = series.dropna().astype(str)
        if non_null.empty:
            continue

        issues: list[str] = []
        n_whitespace = int(non_null.map(lambda v: v != v.strip()).sum())
        n_repeated_spaces = int(non_null.map(lambda v: "  " in v).sum())
        n_mixed_case = int(
            non_null.map(lambda v: v != v.lower() and v != v.upper() and any(c.isalpha() for c in v)).sum()
        )
        n_blank = int(non_null.map(lambda v: v.strip() == "").sum())

        if n_whitespace > 0:
            issues.append(f"{n_whitespace} value(s) with leading/trailing whitespace")
        if n_repeated_spaces > 0:
            issues.append(f"{n_repeated_spaces} value(s) with repeated spaces")
        if n_blank > 0:
            issues.append(f"{n_blank} blank string(s)")

        # Case inconsistency: same word appears in different cases
        casefolded = non_null.str.casefold()
        if casefolded.nunique() < non_null.nunique():
            issues.append("Inconsistent case for repeated values")

        report[str(col)] = {
            "n_whitespace": n_whitespace,
            "n_repeated_spaces": n_repeated_spaces,
            "n_mixed_case": n_mixed_case,
            "n_blank": n_blank,
            "n_unique": int(non_null.nunique()),
            "issues": issues,
        }
    return report


def clean_text(
    data: pd.DataFrame,
    rules: dict[str, dict[str, bool | str]],
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Apply text-cleaning rules to a copy.

    rules maps column -> {
        "trim": bool,
        "collapse_spaces": bool,
        "case": "none"|"lower"|"upper"|"title",
        "standardize": dict[str,str] | None,
        "remove_chars": str | None,
    }

    Returns (cleaned_copy, records). Source is never mutated.
    """
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []

    for column, rule in rules.items():
        if column not in cleaned.columns:
            records.append(CleaningRecord(
                step="Text cleaning",
                column=column,
                operation="clean",
                rows_affected=0,
                parameters=rule,
                succeeded=False,
                warning=f"Column '{column}' not found.",
            ))
            continue

        series = cleaned[column]
        if series.dtype != object and not str(series.dtype).startswith("string"):
            continue

        before = series.astype(str).fillna("")
        working = series.copy()
        changed_mask = pd.Series(False, index=working.index)
        params = dict(rule)

        if rule.get("trim"):
            working = working.map(lambda v: v.strip() if isinstance(v, str) else v)
            changed_mask |= working.astype(str).fillna("") != before

        if rule.get("collapse_spaces"):
            working = working.map(lambda v: " ".join(str(v).split()) if isinstance(v, str) else v)
            changed_mask |= working.astype(str).fillna("") != before

        case = rule.get("case", "none")
        if case != "none":
            if case == "lower":
                working = working.map(lambda v: v.casefold() if isinstance(v, str) else v)
            elif case == "upper":
                working = working.map(lambda v: v.upper() if isinstance(v, str) else v)
            elif case == "title":
                working = working.map(lambda v: v.title() if isinstance(v, str) else v)
            changed_mask |= working.astype(str).fillna("") != before

        standardize = rule.get("standardize")
        if standardize and isinstance(standardize, dict):
            working = working.map(lambda v: standardize.get(str(v).strip(), v) if isinstance(v, str) else v)
            changed_mask |= working.astype(str).fillna("") != before

        remove_chars = rule.get("remove_chars")
        if remove_chars and isinstance(remove_chars, str):
            working = working.map(lambda v: str(v).translate(str.maketrans("", "", remove_chars)) if isinstance(v, str) else v)
            changed_mask |= working.astype(str).fillna("") != before

        n_changed = int(changed_mask.sum())
        cleaned[column] = working

        records.append(CleaningRecord(
            step="Text cleaning",
            column=column,
            operation="clean",
            rows_affected=n_changed,
            parameters=params,
            before_stats={"n_unique": int(series.nunique(dropna=True))},
            after_stats={"n_unique": int(working.nunique(dropna=True))},
            succeeded=True,
        ))

    return cleaned, records
