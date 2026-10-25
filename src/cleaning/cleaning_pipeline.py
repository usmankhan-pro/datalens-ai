"""Cleaning pipeline: orchestrates all cleaning operations with audit trail.

Provides preview-then-apply semantics, undo/reset support, and immutable
source data.  All operations work on copies.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.cleaning.audit import CleaningRecord, CleaningResult
from src.cleaning.data_types import convert_types, detect_column_types, preserve_leading_zeros
from src.cleaning.duplicates import detect_duplicates, preview_duplicates, remove_duplicates
from src.cleaning.missing_values import (
    add_missingness_indicators,
    detect_missing,
    fill_missing,
)
from src.cleaning.outliers import detect_outliers_iqr, detect_outliers_zscore, handle_outliers
from src.cleaning.text_cleaning import clean_text, detect_text_issues


class CleaningPipeline:
    """Manages a sequence of cleaning operations on a working copy.

    The original source DataFrame is kept immutable.  Each operation
    produces a new working copy and appends an audit record.
    """

    def __init__(self, source_data: pd.DataFrame):
        self._source: pd.DataFrame = source_data.copy(deep=True)
        self._source_snapshot: pd.DataFrame = source_data.copy(deep=True)
        self._working: pd.DataFrame = source_data.copy(deep=True)
        self._records: list[CleaningRecord] = []
        self._history: list[pd.DataFrame] = [self._working.copy(deep=True)]
        self._history_record_counts: list[int] = [0]

    @property
    def source(self) -> pd.DataFrame:
        return self._source

    @property
    def working(self) -> pd.DataFrame:
        return self._working

    @property
    def records(self) -> list[CleaningRecord]:
        return list(self._records)

    @property
    def can_undo(self) -> bool:
        return len(self._history) > 1

    def reset(self) -> None:
        """Restore the working copy to the original source data."""
        self._working = self._source.copy(deep=True)
        self._records = []
        self._history = [self._working.copy(deep=True)]
        self._history_record_counts = [0]

    def undo(self) -> bool:
        """Revert to the previous working state.  Returns True if an undo happened."""
        if not self.can_undo:
            return False
        previous = self._history.pop()
        record_count = self._history_record_counts.pop()
        self._working = previous.copy(deep=True)
        del self._records[record_count:]
        return True

    def _snapshot(self) -> None:
        self._history.append(self._working.copy(deep=True))
        self._history_record_counts.append(len(self._records))

    def apply_preview(
        self,
        cleaned_data: pd.DataFrame,
        records: list[CleaningRecord],
    ) -> list[dict[str, Any]]:
        """Commit a user-approved preview as one undoable operation."""
        if not isinstance(cleaned_data, pd.DataFrame):
            raise TypeError("A cleaning preview must contain a pandas DataFrame.")
        self._snapshot()
        self._working = cleaned_data.copy(deep=True)
        self._records.extend(records)
        return [record.to_dict() for record in records]

    # ------------------------------------------------------------------
    # Diagnostics (read-only, no state change)
    # ------------------------------------------------------------------

    def profile_columns(self) -> dict[str, dict[str, Any]]:
        return detect_column_types(self._working)

    def missing_report(self, include_placeholders: bool = True) -> dict[str, dict[str, Any]]:
        return detect_missing(self._working, include_placeholders)

    def duplicate_report(self, subset: list[str] | None = None) -> dict[str, object]:
        return detect_duplicates(self._working, subset)

    def duplicate_preview(
        self,
        subset: list[str] | None = None,
        max_rows: int = 10,
    ) -> pd.DataFrame:
        return preview_duplicates(self._working, subset, max_rows)

    def text_issues(self) -> dict[str, dict[str, object]]:
        return detect_text_issues(self._working)

    def outlier_report_iqr(
        self,
        column: str,
        multiplier: float = 1.5,
    ) -> dict[str, Any]:
        return detect_outliers_iqr(self._working, column, multiplier)

    def outlier_report_zscore(
        self,
        column: str,
        threshold: float = 3.0,
    ) -> dict[str, Any]:
        return detect_outliers_zscore(self._working, column, threshold)

    # ------------------------------------------------------------------
    # Operations (each snapshots before applying)
    # ------------------------------------------------------------------

    def remove_duplicates(
        self,
        subset: list[str] | None = None,
        keep: str = "first",
    ) -> list[dict[str, Any]]:
        cleaned, records = remove_duplicates(self._working, subset=subset, keep=keep)
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def fix_types(
        self,
        conversions: dict[str, str],
    ) -> list[dict[str, Any]]:
        cleaned, records = convert_types(self._working, conversions)
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def preserve_zeros(self, columns: list[str]) -> list[dict[str, Any]]:
        cleaned, records = preserve_leading_zeros(self._working, columns)
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def fill_missing(
        self,
        rules: dict[str, tuple[str, str]],
        include_placeholders: bool = True,
    ) -> list[dict[str, Any]]:
        cleaned, records = fill_missing(
            self._working, rules, include_placeholders=include_placeholders
        )
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def add_missingness_indicators(
        self,
        columns: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        cleaned, records = add_missingness_indicators(self._working, columns)
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def clean_text(
        self,
        rules: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        cleaned, records = clean_text(self._working, rules)
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def handle_outliers(
        self,
        rules: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        cleaned, records = handle_outliers(self._working, rules)
        self._snapshot()
        self._working = cleaned
        self._records.extend(records)
        return [r.to_dict() for r in records]

    def to_result(self) -> CleaningResult:
        return CleaningResult(
            cleaned_data=self._working,
            records=list(self._records),
            source_immutable=self._source.equals(self._source_snapshot),
        )
