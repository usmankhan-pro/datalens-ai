"""Duplicate-row detection and removal."""

from __future__ import annotations

import pandas as pd

from src.cleaning.audit import CleaningRecord


def detect_duplicates(
    data: pd.DataFrame,
    subset: list[str] | None = None,
) -> dict[str, object]:
    """Return duplicate-row statistics.

    subset: columns to consider for identifying duplicates (None = all columns).
    """
    n_rows = len(data)
    dup_mask = data.duplicated(subset=subset, keep=False)
    n_dup_rows = int(dup_mask.sum())
    n_dup_groups = 0
    if n_dup_rows > 0 and subset is not None:
        dup_groups = data[dup_mask].groupby(subset).ngroups
        n_dup_groups = int(dup_groups)
    elif n_dup_rows > 0:
        n_dup_groups = int(data[data.duplicated(keep=False)].groupby(list(data.columns)).ngroups)

    return {
        "n_rows": n_rows,
        "n_duplicate_rows": n_dup_rows,
        "duplicate_pct": round(n_dup_rows / n_rows * 100, 2) if n_rows > 0 else 0.0,
        "n_duplicate_groups": n_dup_groups,
        "n_unique_rows": n_rows - n_dup_rows,
        "subset": subset,
    }


def preview_duplicates(
    data: pd.DataFrame,
    subset: list[str] | None = None,
    max_rows: int = 10,
) -> pd.DataFrame:
    """Return a preview of duplicate rows for inspection."""
    if len(data) == 0:
        return data.iloc[:0].copy()
    dup_mask = data.duplicated(subset=subset, keep=False)
    return data[dup_mask].head(max_rows).copy()


def remove_duplicates(
    data: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str = "first",
) -> tuple[pd.DataFrame, list[CleaningRecord]]:
    """Remove duplicate rows from a copy.

    keep: "first", "last", or False (drop all duplicates).
    subset: columns to consider; None means all columns.
    Returns (cleaned_copy, records). Source is never mutated.
    """
    cleaned = data.copy(deep=True)
    records: list[CleaningRecord] = []

    n_before = len(cleaned)
    dup_mask = cleaned.duplicated(subset=subset, keep=False)
    n_duplicates = int(dup_mask.sum())

    if n_duplicates == 0:
        records.append(CleaningRecord(
            step="Remove duplicates",
            column="All columns" if subset is None else ", ".join(subset),
            operation="remove",
            rows_affected=0,
            parameters={"subset": subset, "keep": keep},
            before_stats={"n_rows": n_before, "n_duplicates": 0},
            after_stats={"n_rows": n_before},
            succeeded=True,
        ))
        return cleaned, records

    cleaned = cleaned.drop_duplicates(subset=subset, keep=keep).copy()
    n_after = len(cleaned)
    removed = n_before - n_after

    records.append(CleaningRecord(
        step="Remove duplicates",
        column="All columns" if subset is None else ", ".join(subset),
        operation="remove",
        rows_affected=removed,
        parameters={"subset": subset, "keep": keep},
        before_stats={"n_rows": n_before, "n_duplicates": n_duplicates},
        after_stats={"n_rows": n_after},
        succeeded=True,
    ))

    return cleaned, records
