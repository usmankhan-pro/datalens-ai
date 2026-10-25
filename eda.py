"""Computed exploratory analysis for tabular datasets."""

from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from plots import draw_box_groups
from cleaning import fix_types


def prepare_eda_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return a typed analysis copy without changing the source."""
    cleaned, _ = fix_types(data)
    return cleaned


def numeric_data(data: pd.DataFrame) -> pd.DataFrame:
    """Return numeric columns plus a binary churn column when available."""
    numeric = data.select_dtypes(include="number").copy()
    for column in data.select_dtypes(include=["object", "string", "category"]):
        if column.casefold() == "churn":
            values = data[column].astype("string").str.strip().str.casefold()
            numeric[column] = values.map({"yes": 1, "no": 0, "true": 1, "false": 0})
    return numeric


def missing_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize missing values by column."""
    counts = data.isna().sum()
    return pd.DataFrame({"missing": counts, "missing_pct": counts.div(len(data)).mul(100)})


def categorical_description(data: pd.DataFrame) -> pd.DataFrame:
    """Describe categorical columns."""
    categorical = data.select_dtypes(include=["object", "string", "category"])
    return categorical.describe().T


def correlations(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate pairwise correlations for numeric analysis columns."""
    return numeric_data(data).corr(numeric_only=True)


def missing_insight(data: pd.DataFrame) -> str:
    """Describe the largest observed missing-value count."""
    missing_columns = missing_summary(data).query("missing > 0")["missing"].sort_values(ascending=False)
    if missing_columns.empty:
        return "No missing values were found in the dataset."
    column = str(missing_columns.index[0])
    count = int(missing_columns.iloc[0])
    return f"{column} has the most missing values ({count:,}, {count / len(data):.1%} of rows)."


def churn_insights(data: pd.DataFrame) -> list[str]:
    """Describe measured churn and month-to-month churn rates."""
    churn_column = next((col for col in data.columns if col.casefold() == "churn"), None)
    if churn_column is None:
        return []
    churn = data[churn_column].astype("string").str.strip().str.casefold().eq("yes")
    insights = [f"The observed churn rate is {churn.mean():.1%} ({int(churn.sum()):,} customers)."]
    contract_column = next((col for col in data.columns if col.casefold() == "contract"), None)
    if contract_column:
        monthly = data[contract_column].astype("string").str.strip().str.casefold().eq("month-to-month")
        if monthly.any():
            insights.append(f"Month-to-month churn is {churn[monthly].mean():.1%} across {int(monthly.sum()):,} customers.")
    return insights


def strongest_association(data: pd.DataFrame) -> str | None:
    """Describe the strongest pairwise numeric correlation."""
    matrix = correlations(data)
    pairs = matrix.where(np.isfinite(matrix) & matrix.abs().lt(1)).stack().dropna()
    if pairs.empty:
        return None
    pair = pairs.abs().idxmax()
    return f"The strongest numeric association is {pair[0]} vs {pair[1]} (correlation {matrix.loc[pair[0], pair[1]]:.2f})."


def insight_text(data: pd.DataFrame) -> list[str]:
    """Generate concise insights from measured dataset values."""
    insights = [f"The dataset contains {len(data):,} rows and {len(data.columns):,} columns.", missing_insight(data)]
    insights.extend(churn_insights(data))
    association = strongest_association(data)
    if association:
        insights.append(association)
    return insights[:5]


def histogram(data: pd.DataFrame, column: str) -> Figure:
    """Create a histogram for one numeric column."""
    figure, axis = plt.subplots()
    axis.hist(data[column].dropna(), bins="auto", color="#287a78", edgecolor="white")
    axis.set(title=f"Distribution of {column}", xlabel=column, ylabel="Count")
    figure.tight_layout()
    return figure


def boxplot(data: pd.DataFrame, column: str) -> Figure:
    """Create an IQR box plot for one numeric column."""
    figure, axis = plt.subplots()
    draw_box_groups(axis, [data[column]], [column], vertical=False)
    axis.set(title=f"Outlier view: {column}", xlabel=column)
    figure.tight_layout()
    return figure


def correlation_heatmap(data: pd.DataFrame) -> Figure:
    """Create a seaborn correlation heatmap."""
    matrix = correlations(data)
    figure, axis = plt.subplots(figsize=(max(7, len(matrix.columns) * 0.55), 6))
    image = axis.imshow(matrix, cmap="vlag", vmin=-1, vmax=1, aspect="auto")
    axis.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
    axis.set_yticks(range(len(matrix.index)), matrix.index)
    figure.colorbar(image, ax=axis, label="Correlation")
    axis.set_title("Numeric correlation matrix")
    figure.tight_layout()
    return figure


def numeric_description(data: pd.DataFrame) -> pd.DataFrame:
    """Describe numeric columns."""
    return numeric_data(data).describe().T


def value_counts(data: pd.DataFrame, column: str) -> pd.Series:
    """Count values in one selected column, including missing values."""
    return data[column].value_counts(dropna=False)
