import pandas as pd

from core.profiling import profile_dataframe
from core.quality import analyze_quality


def test_profile_dataframe_returns_dataset_and_column_summary():
    df = pd.DataFrame(
        {
            "customer_id": ["C001", "C002", "C003"],
            "region": ["North", "South", "North"],
            "amount": [100, 200, 300],
            "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
        }
    )

    result = profile_dataframe(df)

    assert result["rows"] == 3
    assert result["cols"] == 4
    assert "customer_id" in result["columns"]
    assert result["type_counts"]["numeric"] >= 1
    assert result["type_counts"]["datetime"] >= 1


def test_analyze_quality_returns_score_and_grade():
    df = pd.DataFrame({
        "qty": [1, 2, 3, 4, 5],
        "revenue": [10, 20, 30, 40, 50],
        "region": ["North", "North", "South", "South", "South"],
    })

    result = analyze_quality(df)

    assert 0 <= result["overall_score"] <= 100
    assert result["grade"] in {"Excellent", "Good", "Fair", "Poor", "Critical"}
    assert isinstance(result["issues"], list)


def test_quality_detection_flags_duplicates_and_negative_values():
    df = pd.DataFrame({
        "customer_id": ["A", "A", "B"],
        "quantity": [5, -2, 3],
        "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
    })

    result = analyze_quality(df)
    issue_types = {i["type"] for i in result["issues"]}

    assert "duplicate_rows" in issue_types or "duplicate_ids" in issue_types
    assert "negative_values" in issue_types or "impossible_numeric" in issue_types
