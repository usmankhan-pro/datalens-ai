import pandas as pd
from pandas.api.types import is_numeric_dtype

from app import load_demo
from eda import (
    boxplot,
    categorical_description,
    correlation_heatmap,
    correlations,
    histogram,
    insight_text,
    missing_summary,
    numeric_description,
    prepare_eda_data,
    value_counts,
)


def test_telco_expected_eda_values():
    raw = load_demo()
    data = prepare_eda_data(raw)
    churn = data["Churn"].eq("Yes")
    month_to_month = data["Contract"].eq("Month-to-month")
    numeric = correlations(data)

    assert is_numeric_dtype(data["TotalCharges"])
    assert round(churn.mean() * 100, 1) == 26.5
    assert round(churn[month_to_month].mean() * 100, 1) == 42.7
    assert round(numeric.loc["tenure", "TotalCharges"], 2) == 0.83
    assert round(numeric.loc["tenure", "Churn"], 2) == -0.35
    assert raw["TotalCharges"].dtype == "str"


def test_descriptions_missing_and_counts_are_computed():
    data = pd.DataFrame({"number": [1, 2, None], "group": ["a", "b", "a"]})

    assert numeric_description(data).loc["number", "count"] == 2
    assert categorical_description(data).loc["group", "unique"] == 2
    assert missing_summary(data).loc["number", "missing"] == 1
    assert value_counts(data, "group").to_dict() == {"a": 2, "b": 1}


def test_insights_derive_from_supplied_data():
    data = pd.DataFrame({"Churn": ["Yes", "No", "Yes", "No"], "Contract": ["Month-to-month"] * 4})

    insights = insight_text(data)

    assert any("4 rows" in insight for insight in insights)
    assert any("50.0%" in insight for insight in insights)
    assert any("Month-to-month churn is 50.0%" in insight for insight in insights)


def test_plots_render_for_telco_numeric_columns():
    data = prepare_eda_data(load_demo())

    histogram_figure = histogram(data, "tenure")
    box_figure = boxplot(data, "TotalCharges")
    heatmap_figure = correlation_heatmap(data)

    assert histogram_figure.axes
    assert box_figure.axes
    assert heatmap_figure.axes
