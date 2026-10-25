import matplotlib.pyplot as plt
import pandas as pd

from app import load_demo
from eda import prepare_eda_data
from plots import available_graphs, column_kind, figure_png, hue_columns, render_plot, unavailable_reasons


def chart_cases(data: pd.DataFrame) -> list[tuple[str, str | None, str]]:
    """Build every offered chart case for each Telco column."""
    columns = list(data.columns)
    kinds = {column: column_kind(data, column) for column in columns}
    kind_options = {
        "numeric": ["numeric", "categorical"],
        "categorical": ["categorical", "numeric"],
        "date": ["numeric"],
    }
    cases = []
    for x in columns:
        targets = [None]
        for kind in kind_options[kinds[x]]:
            target = next((column for column in columns if column != x and kinds[column] == kind), None)
            if target:
                targets.append(target)
        for y in targets:
            cases.extend((x, y, graph) for graph in available_graphs(data, x, y))
    return cases


def render_cases(data: pd.DataFrame, cases: list[tuple[str, str | None, str]]) -> list[tuple[str, str | None, str, str]]:
    """Render each offered chart and collect any failures."""
    failures = []
    for x, y, graph in cases:
        try:
            figure = render_plot(data, x, graph, y)
            assert figure.axes
            assert figure_png(figure).startswith(b"\x89PNG\r\n\x1a\n")
            plt.close(figure)
        except Exception as error:
            failures.append((x, y, graph, repr(error)))
    return failures


def test_every_telco_column_and_offered_graph_renders():
    full_data = prepare_eda_data(load_demo())
    cases = chart_cases(full_data)
    failures = render_cases(full_data.head(250), cases)
    assert not failures, failures
    assert len(cases) > len(full_data.columns)
    print(f"columns={len(full_data.columns)}, offered_graphs_rendered={len(cases)}, failures={len(failures)}")


def test_date_numeric_pair_offers_and_renders_line():
    data = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=4), "value": [2, 4, 3, 8]})

    assert column_kind(data, "date") == "date"
    assert available_graphs(data, "date", "value") == ["Line"]
    figure = render_plot(data, "date", "Line", "value")
    assert figure_png(figure).startswith(b"\x89PNG\r\n\x1a\n")
    plt.close(figure)


def test_hue_supported_graphs_render_and_incompatible_types_explain():
    data = prepare_eda_data(load_demo()).head(200)
    for x, y, graph in [
        ("tenure", None, "Histogram"),
        ("tenure", "MonthlyCharges", "Scatter"),
        ("Contract", "MonthlyCharges", "Violin"),
        ("Contract", None, "Count"),
    ]:
        hues = hue_columns(data, x, y, graph)
        assert hues
        figure = render_plot(data, x, graph, y, hues[0])
        assert figure_png(figure).startswith(b"\x89PNG\r\n\x1a\n")
        plt.close(figure)

    reasons = unavailable_reasons(data, "tenure", None)
    assert "Pie" in reasons
    assert "categorical X" in reasons["Pie"]


def test_graph_rules_cover_all_requested_axis_types():
    data = pd.DataFrame({
        "number_a": [1, 2, 3],
        "number_b": [3, 2, 1],
        "category_a": ["a", "b", "a"],
        "category_b": ["x", "x", "y"],
        "date": pd.date_range("2025-01-01", periods=3),
    })

    assert available_graphs(data, "number_a") == ["Histogram", "Box", "KDE"]
    assert available_graphs(data, "category_a") == ["Count", "Pie"]
    assert available_graphs(data, "number_a", "number_b") == ["Scatter", "Line", "Heatmap"]
    assert available_graphs(data, "category_a", "number_a") == ["Box", "Violin", "Bar (mean)"]
    assert available_graphs(data, "category_a", "category_b") == ["Grouped bar", "Stacked bar"]
    assert available_graphs(data, "date", "number_a") == ["Line"]
