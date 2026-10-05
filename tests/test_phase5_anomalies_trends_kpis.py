import pandas as pd

from core.anomaly import IQRDetector, ModifiedZScoreDetector, detect_anomalies
from core.kpi import detect_kpis
from core.trends import analyze_trends


def test_iqr_detector_catches_extreme_value():
    s = pd.Series([10, 11, 12, 13, 14, 100])
    detector = IQRDetector()
    anomalies = detector.detect(s)

    assert anomalies
    assert any(item["value"] == 100 for item in anomalies)


def test_detect_anomalies_handles_dataframe():
    df = pd.DataFrame({
        "value": [1, 2, 3, 4, 100],
        "other": [5, 6, 7, 8, 9],
    })
    anomalies = detect_anomalies(df, method="iqr")

    assert anomalies
    assert any(item["column"] == "value" for item in anomalies)


def test_analyze_trends_returns_insufficient_message_without_datetime():
    df = pd.DataFrame({"value": [1, 2, 3, 4]})
    result = analyze_trends(df, date_col="date", value_col="value")

    assert result["status"] == "insufficient"
    assert "Insufficient" in result["reason"]


def test_detect_kpis_uses_revenue_and_profit_columns():
    df = pd.DataFrame({
        "Revenue": [100, 200, 300],
        "Cost": [50, 60, 70],
        "Profit": [50, 140, 230],
        "Customer_ID": [101, 102, 103],
    })
    result = detect_kpis(df)

    names = {item["name"] for item in result}
    assert "Total Revenue" in names
    assert "Total Profit" in names
    assert "Profit Margin" in names
