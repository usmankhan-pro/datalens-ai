"""Plotly chart builders for DataFlow Analytics.

All functions return plotly.graph_objects.Figure objects.  Charts are
type-aware, have readable titles and axis labels, and avoid generating
meaningless visualizations.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def _empty_figure(message: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#666666"),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=40, b=40, l=40, r=40),
        height=400,
    )
    return fig


def histogram(
    data: pd.DataFrame,
    column: str,
    nbins: int = 30,
    color_column: str | None = None,
) -> go.Figure:
    """Histogram for a numeric column."""
    plot_data = data[[column] + ([color_column] if color_column else [])].dropna()
    if plot_data.empty:
        return _empty_figure(f"No data available for {column}.")
    fig = px.histogram(
        plot_data, x=column, color=color_column or None,
        nbins=nbins, title=f"Distribution of {column}",
        labels={column: column, "count": "Count"},
    )
    fig.update_layout(
        bargap=0.1,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=450,
        legend_title_text=color_column or "",
    )
    return fig


def box_plot(
    data: pd.DataFrame,
    column: str,
    category_column: str | None = None,
) -> go.Figure:
    """Box plot for a numeric column, optionally grouped by category."""
    plot_data = data[[column] + ([category_column] if category_column else [])].dropna()
    if plot_data.empty:
        return _empty_figure(f"No data available for {column}.")
    fig = px.box(
        plot_data, y=column, x=category_column or None,
        title=f"Box plot: {column}",
        labels={column: column},
        points="outliers",
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=450,
        xaxis_title=category_column or "",
    )
    return fig


def bar_chart(
    data: pd.DataFrame,
    column: str,
    top_n: int = 20,
    include_missing: bool = False,
) -> go.Figure:
    """Bar chart of value counts for a categorical column."""
    plot_data = data[column]
    if include_missing:
        value_counts = plot_data.value_counts(dropna=False)
    else:
        value_counts = plot_data.value_counts(dropna=True)

    if value_counts.empty:
        return _empty_figure(f"No data available for {column}.")

    top = value_counts.head(top_n)
    fig = px.bar(
        x=top.index.astype(str),
        y=top.values,
        labels={"x": column, "y": "Count"},
        title=f"Top values in {column}",
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=450,
        xaxis_tickangle=-45,
    )
    return fig


def scatter_plot(
    data: pd.DataFrame,
    x: str,
    y: str,
    color_column: str | None = None,
) -> go.Figure:
    """Scatter plot for two numeric columns."""
    plot_data = data[[x, y] + ([color_column] if color_column else [])].dropna()
    if plot_data.empty:
        return _empty_figure(f"No data available for {x} vs {y}.")
    fig = px.scatter(
        plot_data, x=x, y=y, color=color_column or None,
        title=f"{y} vs {x}",
        labels={x: x, y: y},
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=450,
    )
    return fig


def line_chart(
    data: pd.DataFrame,
    x: str,
    y: str,
    color_column: str | None = None,
) -> go.Figure:
    """Line chart, typically for datetime vs numeric."""
    plot_data = data[[x, y] + ([color_column] if color_column else [])].dropna().sort_values(x)
    if plot_data.empty:
        return _empty_figure(f"No data available for {x} vs {y}.")
    fig = px.line(
        plot_data, x=x, y=y, color=color_column or None,
        title=f"{y} over {x}",
        labels={x: x, y: y},
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=450,
    )
    return fig


def heatmap(
    matrix: pd.DataFrame,
    title: str = "Correlation matrix",
) -> go.Figure:
    """Heatmap for a correlation matrix or similar square data."""
    if matrix.empty:
        return _empty_figure("No data for heatmap.")
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=[str(c) for c in matrix.columns],
            y=[str(i) for i in matrix.index],
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(title="Correlation"),
        )
    )
    fig.update_layout(
        title=title,
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=max(400, len(matrix) * 40),
        xaxis_tickangle=-45,
    )
    return fig


def missingness_bar(data: pd.DataFrame) -> go.Figure:
    """Bar chart of missing counts by column."""
    missing = data.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        return _empty_figure("No missing values in any column.")
    fig = px.bar(
        x=missing.index.astype(str),
        y=missing.values,
        labels={"x": "Column", "y": "Missing count"},
        title="Missing values by column",
    )
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=60, b=40, l=40, r=40),
        height=450,
        xaxis_tickangle=-45,
    )
    return fig


def quality_score_gauge(score: float) -> go.Figure:
    """Gauge chart showing the overall quality score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Data Quality Score", "font": {"size": 24}},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkgray"},
            "bar": {"color": "#287a78"},
            "bgcolor": "white",
            "borderwidth": 2,
            "bordercolor": "gray",
            "steps": [
                {"range": [0, 50], "color": "#f4cccc"},
                {"range": [50, 70], "color": "#fff2cc"},
                {"range": [70, 85], "color": "#d9ead3"},
                {"range": [85, 100], "color": "#cfe2f3"},
            ],
            "threshold": {
                "line": {"color": "red", "width": 4},
                "thickness": 0.75,
                "value": 90,
            },
        },
    ))
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        margin=dict(t=40, b=40, l=40, r=40),
        height=300,
    )
    return fig
