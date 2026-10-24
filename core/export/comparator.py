"""Dataset comparison utilities for DataLens AI export and validation.

Computes exact before/after metrics between original and working DataFrames:
- Row and column counts
- Missing percentage
- Duplicate count
- Quality score difference
- Column schema changes (added, removed, renamed, dtype changes)
All metrics are computed strictly from real DataFrame data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd

from core.quality.score import analyze_quality


@dataclass
class DatasetComparison:
    """Exact comparative metrics between before and after DataFrames."""
    before_rows: int
    after_rows: int
    rows_diff: int

    before_cols: int
    after_cols: int
    cols_diff: int

    before_missing_cells: int
    after_missing_cells: int
    before_missing_pct: float
    after_missing_pct: float
    missing_pct_diff: float

    before_duplicates: int
    after_duplicates: int
    duplicates_diff: int

    before_quality_score: float
    after_quality_score: float
    quality_score_diff: float

    added_columns: List[str] = field(default_factory=list)
    removed_columns: List[str] = field(default_factory=list)
    dtype_changes: Dict[str, Dict[str, str]] = field(default_factory=dict)

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert metrics to a display-ready summary dictionary."""
        return {
            "Rows": {
                "Before": self.before_rows,
                "After": self.after_rows,
                "Change": self.rows_diff,
            },
            "Columns": {
                "Before": self.before_cols,
                "After": self.after_cols,
                "Change": self.cols_diff,
            },
            "Missing Values (%)": {
                "Before": round(self.before_missing_pct, 2),
                "After": round(self.after_missing_pct, 2),
                "Change": round(self.missing_pct_diff, 2),
            },
            "Duplicate Rows": {
                "Before": self.before_duplicates,
                "After": self.after_duplicates,
                "Change": self.duplicates_diff,
            },
            "Quality Score": {
                "Before": round(self.before_quality_score, 1),
                "After": round(self.after_quality_score, 1),
                "Change": round(self.quality_score_diff, 1),
            },
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert metrics to a formatted DataFrame for UI tables and export sheets."""
        summary = self.to_summary_dict()
        rows = []
        for metric, vals in summary.items():
            rows.append({
                "Metric": metric,
                "Before": vals["Before"],
                "After": vals["After"],
                "Change": vals["Change"],
            })
        return pd.DataFrame(rows)


def compare_datasets(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    before_score: Optional[float] = None,
    after_score: Optional[float] = None,
) -> DatasetComparison:
    """
    Compare two DataFrames and compute real metric diffs.

    Args:
        before_df: The baseline/original DataFrame.
        after_df: The modified/cleaned working DataFrame.
        before_score: Optional precomputed quality score for before_df.
        after_score: Optional precomputed quality score for after_df.

    Returns:
        DatasetComparison with computed delta metrics.
    """
    b_rows = len(before_df) if before_df is not None else 0
    a_rows = len(after_df) if after_df is not None else 0
    b_cols = len(before_df.columns) if before_df is not None else 0
    a_cols = len(after_df.columns) if after_df is not None else 0

    # Missing counts and percentages
    b_total_cells = b_rows * b_cols
    a_total_cells = a_rows * a_cols

    b_missing_cells = int(before_df.isna().sum().sum()) if before_df is not None else 0
    a_missing_cells = int(after_df.isna().sum().sum()) if after_df is not None else 0

    b_missing_pct = (b_missing_cells / b_total_cells * 100.0) if b_total_cells > 0 else 0.0
    a_missing_pct = (a_missing_cells / a_total_cells * 100.0) if a_total_cells > 0 else 0.0

    # Duplicates
    b_dups = int(before_df.duplicated().sum()) if before_df is not None and b_rows > 0 else 0
    a_dups = int(after_df.duplicated().sum()) if after_df is not None and a_rows > 0 else 0

    # Quality scores
    if before_score is None:
        if before_df is not None and not before_df.empty:
            before_score = float(analyze_quality(before_df).get("overall_score", 100.0))
        else:
            before_score = 100.0

    if after_score is None:
        if after_df is not None and not after_df.empty:
            after_score = float(analyze_quality(after_df).get("overall_score", 100.0))
        else:
            after_score = 100.0

    # Schema changes
    b_col_set = set(before_df.columns) if before_df is not None else set()
    a_col_set = set(after_df.columns) if after_df is not None else set()

    added_cols = sorted(list(a_col_set - b_col_set))
    removed_cols = sorted(list(b_col_set - a_col_set))

    dtype_changes: Dict[str, Dict[str, str]] = {}
    if before_df is not None and after_df is not None:
        common_cols = b_col_set.intersection(a_col_set)
        for col in sorted(list(common_cols)):
            b_type = str(before_df[col].dtype)
            a_type = str(after_df[col].dtype)
            if b_type != a_type:
                dtype_changes[col] = {"before": b_type, "after": a_type}

    return DatasetComparison(
        before_rows=b_rows,
        after_rows=a_rows,
        rows_diff=a_rows - b_rows,
        before_cols=b_cols,
        after_cols=a_cols,
        cols_diff=a_cols - b_cols,
        before_missing_cells=b_missing_cells,
        after_missing_cells=a_missing_cells,
        before_missing_pct=b_missing_pct,
        after_missing_pct=a_missing_pct,
        missing_pct_diff=a_missing_pct - b_missing_pct,
        before_duplicates=b_dups,
        after_duplicates=a_dups,
        duplicates_diff=a_dups - b_dups,
        before_quality_score=before_score,
        after_quality_score=after_score,
        quality_score_diff=after_score - before_score,
        added_columns=added_cols,
        removed_columns=removed_cols,
        dtype_changes=dtype_changes,
    )
