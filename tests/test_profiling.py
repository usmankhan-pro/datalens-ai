"""Tests for the profiling module (Phase 1).

Covers: normal mixed-type data, missing values, duplicate rows, empty /
all-null columns, constant columns, numeric strings, date-like strings,
empty datasets, unusual column names, and immutability of the source
DataFrame.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from profiling import (
    find_quality_findings,
    profile_columns,
    profile_dataset,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mixed_df() -> pd.DataFrame:
    """A small mixed-type dataset with no duplicate rows."""
    return pd.DataFrame({
        "age": [25, 30, None, 40, 35],
        "score": [88.5, 92.0, 78.0, None, 71.0],
        "city": ["Boston", "NYC", "Boston", None, "LA"],
        "joined": pd.to_datetime(["2020-01-01", "2021-06-15", "2019-03-22", "2022-11-01", "2023-05-10"]),
        "active": [True, True, False, True, False],
    })


@pytest.fixture()
def numeric_string_df() -> pd.DataFrame:
    return pd.DataFrame({"amount": ["10.5", "20", "30.0", None, "40"]})


@pytest.fixture()
def date_string_df() -> pd.DataFrame:
    return pd.DataFrame({
        "event_date": ["2023-01-01", "2023-06-15", "2022-12-31", "2024-03-10", None]
    })


# ---------------------------------------------------------------------------
# profile_dataset – dataset-level stats
# ---------------------------------------------------------------------------

class TestProfileDataset:
    def test_shape_reported_correctly(self, mixed_df):
        result = profile_dataset(mixed_df)
        assert result["n_rows"] == 5
        assert result["n_cols"] == 5

    def test_no_duplicates_in_mixed_df(self, mixed_df):
        result = profile_dataset(mixed_df)
        assert result["n_duplicates"] == 0

    def test_duplicate_rows_counted(self):
        df = pd.DataFrame({"a": [1, 2, 1], "b": ["x", "y", "x"]})
        result = profile_dataset(df)
        assert result["n_duplicates"] == 1

    def test_missing_cells_counted(self, mixed_df):
        # age:1, score:1, city:1 = 3 missing
        result = profile_dataset(mixed_df)
        assert result["n_missing_cells"] == 3

    def test_missing_pct_is_proportion_of_all_cells(self, mixed_df):
        result = profile_dataset(mixed_df)
        expected = round(3 / (5 * 5) * 100, 2)
        assert result["missing_pct"] == expected

    def test_empty_rows_counted(self):
        df = pd.DataFrame({"a": [1, None, None], "b": [2, None, None]})
        result = profile_dataset(df)
        assert result["n_empty_rows"] == 2

    def test_empty_column_detected(self):
        df = pd.DataFrame({"a": [1, 2], "b": [None, None]})
        result = profile_dataset(df)
        assert result["n_empty_cols"] == 1

    def test_constant_column_detected(self):
        df = pd.DataFrame({"a": [1, 1, 1], "b": [2, 3, 4]})
        result = profile_dataset(df)
        assert result["n_constant_cols"] == 1

    def test_unique_per_column_reported(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": ["x", "y", "x"]})
        result = profile_dataset(df)
        assert result["unique_per_column"]["a"] == 2
        assert result["unique_per_column"]["b"] == 2

    def test_duplicate_column_names_detected(self):
        # pandas allows duplicate column names via from_dict trick
        df = pd.DataFrame([[1, 2]], columns=["id", "id"])
        result = profile_dataset(df)
        assert "id" in result["duplicate_column_names"]

    def test_memory_label_is_non_empty_string(self, mixed_df):
        result = profile_dataset(mixed_df)
        assert isinstance(result["memory_label"], str)
        assert len(result["memory_label"]) > 0

    def test_empty_dataframe_returns_zero_rows(self):
        df = pd.DataFrame({"a": [], "b": []})
        result = profile_dataset(df)
        assert result["n_rows"] == 0
        assert result["n_duplicates"] == 0
        assert result["n_missing_cells"] == 0

    def test_source_is_not_mutated(self, mixed_df):
        before = mixed_df.copy(deep=True)
        profile_dataset(mixed_df)
        assert mixed_df.equals(before)


# ---------------------------------------------------------------------------
# profile_columns – per-column metrics
# ---------------------------------------------------------------------------

class TestProfileColumns:
    def test_returns_one_row_per_column(self, mixed_df):
        result = profile_columns(mixed_df)
        assert list(result.index) == [str(c) for c in mixed_df.columns]

    def test_numeric_stats_computed(self, mixed_df):
        result = profile_columns(mixed_df)
        age = result.loc["age"]
        assert age["min"] == 25.0
        assert age["max"] == 40.0
        assert age["median"] == 32.5
        assert age["n_missing"] == 1

    def test_missing_pct_for_numeric(self, mixed_df):
        result = profile_columns(mixed_df)
        # age: 1 missing out of 5 rows = 20%
        assert result.loc["age", "missing_pct"] == 20.0

    def test_categorical_top_categories(self, mixed_df):
        result = profile_columns(mixed_df)
        city = result.loc["city"]
        assert isinstance(city["top_categories"], dict)
        assert "Boston" in city["top_categories"] or "NYC" in city["top_categories"]

    def test_datetime_date_range(self, mixed_df):
        result = profile_columns(mixed_df)
        joined = result.loc["joined"]
        assert joined["date_min"] is not None
        assert joined["date_max"] is not None
        assert joined["date_min"] <= joined["date_max"]

    def test_all_null_column_flagged(self):
        df = pd.DataFrame({"a": [1, 2], "b": [None, None]})
        result = profile_columns(df)
        assert result.loc["b", "is_all_null"] is True or result.loc["b", "is_all_null"] == True

    def test_constant_column_flagged(self):
        df = pd.DataFrame({"a": [7, 7, 7]})
        result = profile_columns(df)
        assert result.loc["a", "is_constant"] is True or result.loc["a", "is_constant"] == True

    def test_numeric_string_column_flagged(self, numeric_string_df):
        result = profile_columns(numeric_string_df)
        assert result.loc["amount", "is_numeric_string"] is True or result.loc["amount", "is_numeric_string"] == True

    def test_date_string_column_flagged(self, date_string_df):
        result = profile_columns(date_string_df)
        assert result.loc["event_date", "is_date_string"] is True or result.loc["event_date", "is_date_string"] == True

    def test_numeric_dtype_does_not_flag_date_or_numeric_string(self, mixed_df):
        result = profile_columns(mixed_df)
        assert not result.loc["age", "is_numeric_string"]
        assert not result.loc["age", "is_date_string"]

    def test_empty_dataframe_returns_empty_profile(self):
        df = pd.DataFrame()
        result = profile_columns(df)
        assert result.empty

    def test_columns_with_special_names(self):
        df = pd.DataFrame({"col with spaces": [1, 2], "123": [3, 4], "": [5, 6]})
        result = profile_columns(df)
        assert len(result) == 3

    def test_source_not_mutated(self, mixed_df):
        before = mixed_df.copy(deep=True)
        profile_columns(mixed_df)
        assert mixed_df.equals(before)

    def test_n_unique_excludes_nulls(self):
        df = pd.DataFrame({"x": [1, 1, None, 2]})
        result = profile_columns(df)
        assert result.loc["x", "n_unique"] == 2

    def test_quartiles_present_for_numeric(self, mixed_df):
        result = profile_columns(mixed_df)
        age = result.loc["age"]
        assert age["q1"] is not None
        assert age["q3"] is not None
        assert age["q1"] <= age["median"] <= age["q3"]

    def test_std_is_none_for_all_null(self):
        df = pd.DataFrame({"x": [None, None]})
        result = profile_columns(df)
        assert result.loc["x", "std"] is None or (
            result.loc["x", "std"] is not None and pd.isna(result.loc["x", "std"])
        )

    def test_large_dataframe_does_not_crash(self):
        df = pd.DataFrame({
            "num": np.random.randn(10_000),
            "cat": np.random.choice(["a", "b", "c"], 10_000),
        })
        result = profile_columns(df)
        assert len(result) == 2

    def test_boolean_column_handled(self, mixed_df):
        result = profile_columns(mixed_df)
        # boolean is numeric in pandas; should not error
        assert "active" in result.index


# ---------------------------------------------------------------------------
# find_quality_findings – findings engine
# ---------------------------------------------------------------------------

class TestFindQualityFindings:
    def test_no_findings_for_clean_dataframe(self):
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        findings = find_quality_findings(df)
        severities = {f["severity"] for f in findings}
        # should have no HIGH or MEDIUM
        assert "HIGH" not in severities
        assert "MEDIUM" not in severities

    def test_empty_dataset_produces_high_finding(self):
        df = pd.DataFrame({"a": [], "b": []})
        findings = find_quality_findings(df)
        assert any(f["severity"] == "HIGH" and "empty" in f["title"].lower() for f in findings)

    def test_duplicate_rows_finding(self):
        df = pd.DataFrame({"a": [1, 2, 1], "b": ["x", "y", "x"]})
        findings = find_quality_findings(df)
        assert any(f["title"] == "Duplicate rows" for f in findings)

    def test_duplicate_column_names_finding(self):
        df = pd.DataFrame([[1, 2, 3]], columns=["a", "b", "a"])
        findings = find_quality_findings(df)
        assert any("Duplicate column names" in f["title"] for f in findings)

    def test_all_null_column_is_high(self):
        df = pd.DataFrame({"a": [1, 2], "b": [None, None]})
        findings = find_quality_findings(df)
        assert any(
            f["severity"] == "HIGH" and "entirely empty" in f["title"]
            for f in findings
        )

    def test_constant_column_is_low(self):
        df = pd.DataFrame({"a": [5, 5, 5], "b": [1, 2, 3]})
        findings = find_quality_findings(df)
        assert any(
            f["severity"] == "LOW" and "Constant" in f["title"]
            for f in findings
        )

    def test_missing_values_severity_thresholds(self):
        # 50% missing -> HIGH
        df_high = pd.DataFrame({"x": [1, None, None, None, None, None]})
        findings_high = find_quality_findings(df_high)
        assert any(f["severity"] == "HIGH" and f["column"] == "x" for f in findings_high)

        # 25% missing -> MEDIUM
        df_med = pd.DataFrame({"x": [1, 2, 3, None]})
        findings_med = find_quality_findings(df_med)
        assert any(f["severity"] == "MEDIUM" and f["column"] == "x" for f in findings_med)

        # 10% missing -> LOW
        df_low = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8, 9, None]})
        findings_low = find_quality_findings(df_low)
        assert any(f["severity"] == "LOW" and f["column"] == "x" for f in findings_low)

    def test_numeric_string_finding(self, numeric_string_df):
        findings = find_quality_findings(numeric_string_df)
        assert any("Numeric values stored as text" in f["title"] for f in findings)

    def test_date_string_finding(self, date_string_df):
        findings = find_quality_findings(date_string_df)
        assert any("Date-like values stored as text" in f["title"] for f in findings)

    def test_high_cardinality_finding(self):
        # each row has a unique string -> cardinality ~ 100%
        df = pd.DataFrame({"uid": [f"user_{i}" for i in range(50)]})
        findings = find_quality_findings(df)
        assert any("cardinality" in f["title"].lower() for f in findings)

    def test_findings_sorted_by_severity_then_column(self):
        df = pd.DataFrame({
            "a": [None, None, None],   # HIGH missing
            "b": [None, None, None],   # HIGH missing
        })
        findings = find_quality_findings(df)
        severities = [f["severity"] for f in findings]
        order = [{"HIGH": 0, "MEDIUM": 1, "LOW": 2, "INFO": 3}[s] for s in severities]
        assert order == sorted(order)

    def test_finding_keys_always_present(self, mixed_df):
        findings = find_quality_findings(mixed_df)
        for f in findings:
            assert set(f.keys()) == {"severity", "column", "title", "detail", "suggestion"}

    def test_source_not_mutated_by_findings(self, mixed_df):
        before = mixed_df.copy(deep=True)
        find_quality_findings(mixed_df)
        assert mixed_df.equals(before)

    def test_accepts_precomputed_col_profiles(self, mixed_df):
        """Passing pre-built col_profiles avoids double computation."""
        cp = profile_columns(mixed_df)
        findings_a = find_quality_findings(mixed_df)
        findings_b = find_quality_findings(mixed_df, col_profiles=cp)
        assert findings_a == findings_b

    def test_completely_empty_rows_finding(self):
        df = pd.DataFrame({"a": [1, None], "b": [2, None]})
        findings = find_quality_findings(df)
        assert any("empty rows" in f["title"].lower() for f in findings)

    def test_telco_demo_findings_are_stable(self):
        """Smoke test: profiling the full Telco demo must not crash and must
        produce at least one finding (TotalCharges is numeric-as-string)."""
        from app import load_demo
        data = load_demo()
        before = data.copy(deep=True)
        findings = find_quality_findings(data)
        assert data.equals(before), "load_demo data was mutated"
        assert len(findings) >= 1
        # Telco has missing TotalCharges and a numeric-string column
        titles = [f["title"] for f in findings]
        assert any("Missing values" in t or "Numeric values stored" in t for t in titles)
