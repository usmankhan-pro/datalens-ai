import pandas as pd

from core.insights import generate_insights, generate_recommendations, build_dashboard_summary


def test_generate_insights_returns_traceable_items():
    df = pd.DataFrame({
        "Revenue": [100, 120, 130, 115],
        "Cost": [60, 70, 75, 80],
        "Region": ["North", "North", "South", "South"],
    })
    results = generate_insights(df)

    assert results
    assert all("source_metric" in item for item in results)
    assert all("text" in item for item in results)


def test_generate_recommendations_maps_to_issues():
    issues = [
        {"type": "missing_values", "column": "Revenue", "severity": "HIGH", "affected_pct": 10},
        {"type": "duplicate_rows", "column": "dataset", "severity": "MEDIUM", "affected_pct": 2},
    ]
    recommendations = generate_recommendations(issues)

    assert recommendations
    assert any("Revenue" in item["text"] for item in recommendations)


def test_dashboard_summary_creates_key_sections():
    df = pd.DataFrame({
        "Revenue": [1000, 1200, 900],
        "Cost": [500, 600, 550],
        "Region": ["North", "South", "North"],
    })
    summary = build_dashboard_summary(df)

    assert "quality_score" in summary
    assert "rows" in summary
    assert "insights" in summary
    assert "recommendations" in summary
