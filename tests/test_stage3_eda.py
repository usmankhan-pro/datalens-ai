from pathlib import Path

import pandas as pd
from pandas.api.types import is_numeric_dtype
from streamlit.testing.v1 import AppTest

from app import load_demo
from src.analysis.correlation import pairwise_correlations
from src.visualization.chart_selector import (
    recommend_correlation_chart,
    recommend_pair_chart,
)
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


def test_pair_chart_selector_handles_unselected_or_missing_columns():
    data = pd.DataFrame({"value": [1, 2, 3]})

    assert recommend_pair_chart(data, "value", None) == []
    assert recommend_pair_chart(data, "value", "missing") == []


def test_correlations_exclude_identifier_candidates_by_default_but_allow_explicit_selection():
    data = pd.DataFrame(
        {
            "customer_id": [101, 102, 103, 104],
            "amount": [10, 20, 10, 30],
            "score": [8, 7, 8, 9],
            "valid": [1, 2, 3, 2],
        }
    )

    default_result = pairwise_correlations(data)
    explicit_result = pairwise_correlations(
        data,
        columns=["customer_id", "amount"],
    )

    assert default_result["columns"] == ["amount", "score", "valid"]
    assert explicit_result["columns"] == ["customer_id", "amount"]
    assert any("pass columns explicitly" in warning for warning in default_result["warnings"])


def test_correlations_warn_when_pair_has_insufficient_complete_samples():
    data = pd.DataFrame({"left": [1, 2, 3], "right": [2, 4, None]})

    result = pairwise_correlations(data)

    assert result["sample_sizes"]["left"]["right"] == 2
    assert any("fewer than 3 complete observations" in warning for warning in result["warnings"])


def test_correlation_chart_recommendation_uses_non_identifier_numeric_columns():
    data = pd.DataFrame(
        {
            "customer_id": [101, 102, 103],
            "amount": [10, 20, 30],
        }
    )

    recommendation = recommend_correlation_chart(data)

    assert recommendation["recommended"] is False
    assert recommendation["columns"] == ["amount"]


def test_app_eda_handles_single_column_dataset():
    app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py"))
    app.session_state["data"] = pd.DataFrame({"Subscribers gained": [48, 57, 40]})
    app.session_state["source"] = "subs.csv"
    app.session_state["active_workspace"] = "Exploratory Data Analysis (EDA)"

    app.run(timeout=30)

    assert not app.exception
