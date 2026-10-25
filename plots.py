"""Type-aware chart options and matplotlib renderers."""

from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype

GRAPH_TYPES = [
    "Histogram", "Box", "KDE", "Count", "Pie", "Scatter", "Line", "Heatmap",
    "Violin", "Bar (mean)", "Grouped bar", "Stacked bar",
]
HUE_GRAPHS = {"Histogram", "Box", "KDE", "Count", "Scatter", "Line", "Violin", "Bar (mean)"}


def column_kind(data: pd.DataFrame, column: str) -> str:
    """Classify a column as numeric, date, or categorical."""
    values = data[column].dropna()
    if is_datetime64_any_dtype(values.dtype):
        return "date"
    if is_numeric_dtype(values.dtype):
        return "numeric"
    parsed = pd.to_datetime(values.astype(str), errors="coerce", format="mixed")
    named_date = any(token in column.casefold() for token in ("date", "time", "timestamp"))
    if len(values) and parsed.notna().mean() >= 0.9 and (named_date or parsed.nunique() > 1):
        return "date"
    return "categorical"


def available_graphs(data: pd.DataFrame, x: str, y: str | None = None) -> list[str]:
    """Return chart types supported by the selected axes."""
    x_kind = column_kind(data, x)
    if y is None:
        return ["Histogram", "Box", "KDE"] if x_kind == "numeric" else ["Count", "Pie"] if x_kind == "categorical" else []
    y_kind = column_kind(data, y)
    kinds = {x_kind, y_kind}
    if kinds == {"numeric"}:
        return ["Scatter", "Line", "Heatmap"]
    if kinds == {"date", "numeric"}:
        return ["Line"]
    if kinds == {"categorical", "numeric"}:
        return ["Box", "Violin", "Bar (mean)"]
    if kinds == {"categorical"}:
        return ["Grouped bar", "Stacked bar"]
    return []


def unavailable_reasons(data: pd.DataFrame, x: str, y: str | None) -> dict[str, str]:
    """Explain the axis requirements for graph types not offered."""
    offered = set(available_graphs(data, x, y))
    requirements = {
        "Histogram": "one numeric X and no Y", "Box": "one numeric X, or categorical and numeric axes",
        "KDE": "one numeric X and no Y", "Count": "one categorical X and no Y",
        "Pie": "one categorical X and no Y", "Scatter": "two numeric axes",
        "Line": "two numeric axes or one date and one numeric axis", "Heatmap": "two numeric axes",
        "Violin": "one categorical and one numeric axis", "Bar (mean)": "one categorical and one numeric axis",
        "Grouped bar": "two categorical axes", "Stacked bar": "two categorical axes",
    }
    return {graph: f"{graph} needs {need}." for graph, need in requirements.items() if graph not in offered}


def hue_columns(data: pd.DataFrame, x: str, y: str | None, graph: str) -> list[str]:
    """Return low-cardinality categorical columns usable as hue."""
    if graph not in HUE_GRAPHS:
        return []
    axes = {x, y}
    return [column for column in data.columns if column not in axes and column_kind(data, column) == "categorical" and data[column].nunique() <= 20]


def _category_values(data: pd.DataFrame, column: str, limit: int = 15) -> list[object]:
    """Select the most frequent categories for a readable chart."""
    return data[column].value_counts().head(limit).index.tolist()


def draw_box_groups(axis, groups: list[pd.Series], labels: list[str], vertical: bool = True) -> None:
    """Draw box-and-whisker summaries without deprecated plotting arguments."""
    for position, group in enumerate(groups, start=1):
        values = group.dropna().to_numpy()
        if not len(values):
            continue
        q1, median, q3 = pd.Series(values).quantile([0.25, 0.5, 0.75])
        spread = q3 - q1
        low = values[values >= q1 - 1.5 * spread].min()
        high = values[values <= q3 + 1.5 * spread].max()
        fliers = values[(values < low) | (values > high)]
        if vertical:
            axis.add_patch(Rectangle((position - 0.25, q1), 0.5, q3 - q1, facecolor="#d8894a", alpha=0.7))
            axis.plot([position - 0.25, position + 0.25], [median, median], color="black")
            axis.plot([position, position], [low, q1], [position, position], [q3, high], color="black")
            axis.scatter([position] * len(fliers), fliers, color="black", s=12)
        else:
            axis.add_patch(Rectangle((q1, position - 0.25), q3 - q1, 0.5, facecolor="#d8894a", alpha=0.7))
            axis.plot([median, median], [position - 0.25, position + 0.25], color="black")
            axis.plot([low, q1], [position, position], [q3, high], [position, position], color="black")
            axis.scatter(fliers, [position] * len(fliers), color="black", s=12)
    ticks = range(1, len(labels) + 1)
    (axis.set_xticks if vertical else axis.set_yticks)(ticks, labels)


def _draw_single(axis, data: pd.DataFrame, x: str, graph: str, hue: str | None) -> None:
    """Draw a one-column chart."""
    if graph == "Histogram":
        sns.histplot(data=data, x=x, hue=hue, bins=25, ax=axis)
    elif graph == "Box":
        draw_box_groups(axis, [data[x]], [x], vertical=False)
    elif graph == "KDE":
        sns.kdeplot(data=data, x=x, hue=hue, ax=axis)
    elif graph == "Count":
        order = _category_values(data, x)
        sns.countplot(data=data, x=x, hue=hue, order=order, ax=axis)
    else:
        counts = data[x].value_counts().head(12)
        counts.plot.pie(ax=axis, ylabel="", autopct="%1.1f%%")


def _draw_numeric_pair(axis, data: pd.DataFrame, x: str, y: str, graph: str, hue: str | None) -> None:
    """Draw numeric or date versus numeric charts."""
    if graph == "Scatter":
        sns.scatterplot(data=data, x=x, y=y, hue=hue, ax=axis)
    elif graph == "Line":
        sns.lineplot(data=data, x=x, y=y, hue=hue, ax=axis)
    else:
        sns.histplot(data=data, x=x, y=y, bins=25, cbar=True, ax=axis)


def _draw_mixed_pair(axis, data: pd.DataFrame, x: str, y: str, graph: str, hue: str | None) -> None:
    """Draw categorical versus numeric charts regardless of axis order."""
    category = x if column_kind(data, x) == "categorical" else y
    number = y if category == x else x
    selected = _category_values(data, category)
    subset = data[data[category].isin(selected)]
    if graph == "Box":
        groups = [subset.loc[subset[category] == value, number] for value in selected]
        draw_box_groups(axis, groups, [str(value) for value in selected])
    elif graph == "Violin":
        sns.violinplot(data=subset, x=category, y=number, hue=hue, ax=axis)
    else:
        sns.barplot(data=subset, x=category, y=number, hue=hue, estimator="mean", errorbar=None, ax=axis)
        axis.set_ylabel(f"Mean {number}")


def _draw_category_pair(axis, data: pd.DataFrame, x: str, y: str, graph: str) -> None:
    """Draw grouped or stacked categorical counts."""
    x_values = _category_values(data, x, 12)
    y_values = _category_values(data, y, 12)
    counts = pd.crosstab(data[x], data[y]).reindex(index=x_values, columns=y_values, fill_value=0)
    counts.plot(kind="bar", stacked=graph == "Stacked bar", ax=axis)
    axis.set_ylabel("Count")


def render_plot(data: pd.DataFrame, x: str, graph: str, y: str | None = None, hue: str | None = None) -> Figure:
    """Render one supported chart and return its matplotlib figure."""
    if graph not in available_graphs(data, x, y):
        raise ValueError(f"{graph} is not available for the selected columns.")
    columns = [column for column in (x, y, hue) if column is not None]
    plot_data = data[columns].dropna().copy()
    figure, axis = plt.subplots(figsize=(9, 5))
    if y is None:
        _draw_single(axis, plot_data, x, graph, hue)
    elif "categorical" in {column_kind(data, x), column_kind(data, y)} and "numeric" in {column_kind(data, x), column_kind(data, y)}:
        _draw_mixed_pair(axis, plot_data, x, y, graph, hue)
    elif column_kind(data, x) == "categorical" and column_kind(data, y) == "categorical":
        _draw_category_pair(axis, plot_data, x, y, graph)
    else:
        _draw_numeric_pair(axis, plot_data, x, y, graph, hue)
    axis.set_title(f"{graph}: {x}" + (f" vs {y}" if y else ""))
    if y is not None and column_kind(data, x) == "categorical" and column_kind(data, y) == "numeric":
        axis.set_xlabel(x)
        axis.set_ylabel(y)
    axis.tick_params(axis="x", labelrotation=35)
    figure.tight_layout()
    return figure


def figure_png(figure: Figure) -> bytes:
    """Encode a matplotlib figure as PNG bytes."""
    output = BytesIO()
    figure.savefig(output, format="png", dpi=160, bbox_inches="tight")
    return output.getvalue()
