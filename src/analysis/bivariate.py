"""Bivariate analysis for pairs of columns."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_numeric_dtype


def _kind(series: pd.Series) -> str:
    if is_datetime64_any_dtype(series.dtype):
        return "datetime"
    if is_numeric_dtype(series.dtype):
        return "numeric"
    return "categorical"


def numeric_vs_numeric(data: pd.DataFrame, x: str, y: str) -> dict[str, Any]:
    """Scatter-ready summary and correlation for two numeric columns."""
    sub = data[[x, y]].dropna()
    n = len(sub)
    if n == 0:
        return {"x": x, "y": y, "n": 0, "correlation": None}

    corr = float(sub[x].corr(sub[y]))
    return {
        "x": x,
        "y": y,
        "n": n,
        "n_missing_x": int(data[x].isna().sum()),
        "n_missing_y": int(data[y].isna().sum()),
        "correlation": round(corr, 4),
        "correlation_pct": round(corr * 100, 2),
        "x_mean": float(sub[x].mean()),
        "y_mean": float(sub[y].mean()),
        "x_std": float(sub[x].std()),
        "y_std": float(sub[y].std()),
        "recommendation": "Scatter plot to inspect the relationship.",
    }


def numeric_vs_categorical(
    data: pd.DataFrame,
    numeric_col: str,
    cat_col: str,
) -> dict[str, Any]:
    """Grouped summary of a numeric column by a categorical column."""
    sub = data[[numeric_col, cat_col]].dropna()
    if sub.empty:
        return {
            "numeric": numeric_col,
            "categorical": cat_col,
            "n": 0,
            "groups": {},
        }

    grouped = sub.groupby(cat_col)[numeric_col].agg(["count", "mean", "min", "max", "std"])
    groups = {
        str(k): {
            "count": int(v["count"]),
            "mean": round(float(v["mean"]), 4),
            "min": round(float(v["min"]), 4),
            "max": round(float(v["max"]), 4),
            "std": round(float(v["std"]), 4) if pd.notna(v["std"]) else None,
        }
        for k, v in grouped.iterrows()
    }

    # Overall ANOVA-like F statistic (between-group vs within-group variance)
    overall_mean = float(sub[numeric_col].mean())
    ss_between = sum(
        g["count"] * (g["mean"] - overall_mean) ** 2 for g in groups.values()
    )
    ss_within = sum(
        (g["count"] - 1) * (g["std"] or 0) ** 2 for g in groups.values()
    )
    df_between = len(groups) - 1
    df_within = len(sub) - len(groups)
    f_stat = None
    if df_between > 0 and df_within > 0 and ss_within > 0:
        ms_between = ss_between / df_between
        ms_within = ss_within / df_within
        f_stat = round(ms_between / ms_within, 4)

    return {
        "numeric": numeric_col,
        "categorical": cat_col,
        "n": int(len(sub)),
        "n_groups": len(groups),
        "groups": groups,
        "overall_mean": round(overall_mean, 4),
        "f_statistic": f_stat,
        "recommendation": "Box plot to compare distributions across categories.",
    }


def categorical_vs_categorical(
    data: pd.DataFrame,
    x: str,
    y: str,
) -> dict[str, Any]:
    """Contingency table and chi-square-friendly summary for two categorical columns."""
    sub = data[[x, y]].dropna()
    if sub.empty:
        return {"x": x, "y": y, "n": 0, "contingency": {}}

    crosstab = pd.crosstab(sub[x], sub[y])
    contingency = {
        str(k): {str(kk): int(vv) for kk, vv in row.items()}
        for k, row in crosstab.iterrows()
    }

    row_totals = crosstab.sum(axis=1)
    col_totals = crosstab.sum(axis=0)
    grand_total = float(crosstab.values.sum())

    # Cramer's V
    chi2 = 0.0
    for i, row_label in enumerate(crosstab.index):
        for j, col_label in enumerate(crosstab.columns):
            observed = int(crosstab.iloc[i, j])
            expected = float(row_totals.iloc[i] * col_totals.iloc[j] / grand_total)
            if expected > 0:
                chi2 += (observed - expected) ** 2 / expected

    min_dim = min(crosstab.shape) - 1
    cramers_v = None
    if chi2 > 0 and grand_total > 0 and min_dim > 0:
        cramers_v = round((chi2 / grand_total / min_dim) ** 0.5, 4)

    return {
        "x": x,
        "y": y,
        "n": int(grand_total),
        "n_x_categories": int(len(crosstab.index)),
        "n_y_categories": int(len(crosstab.columns)),
        "contingency": contingency,
        "chi2": round(chi2, 4),
        "cramers_v": cramers_v,
        "recommendation": "Stacked or grouped bar chart to compare category distributions.",
    }


def datetime_vs_numeric(
    data: pd.DataFrame,
    date_col: str,
    numeric_col: str,
) -> dict[str, Any]:
    """Time-series summary: numeric values aggregated over time."""
    sub = data[[date_col, numeric_col]].dropna()
    if sub.empty:
        return {"date": date_col, "numeric": numeric_col, "n": 0}

    dates = pd.to_datetime(sub[date_col])
    values = sub[numeric_col].astype(float)
    df = pd.DataFrame({"date": dates, "value": values}).sort_values("date")

    # Resample to daily if there are enough points
    if len(df) > 1:
        daily = df.set_index("date").resample("D")["value"].agg(["count", "mean"]).dropna()
    else:
        daily = df.set_index("date")["value"].agg(["count", "mean"]).to_frame().T

    return {
        "date": date_col,
        "numeric": numeric_col,
        "n": int(len(df)),
        "date_min": str(df["date"].min()),
        "date_max": str(df["date"].max()),
        "trend": "increasing" if len(df) > 1 and float(df["value"].iloc[-1]) > float(df["value"].iloc[0]) else ("decreasing" if len(df) > 1 else "flat"),
        "daily_points": int(len(daily)),
        "recommendation": "Line plot to inspect values over time.",
    }


def analyze_pair(
    data: pd.DataFrame,
    col_a: str,
    col_b: str,
) -> dict[str, Any]:
    """Auto-detect column types and dispatch to the appropriate bivariate analysis."""
    kind_a = _kind(data[col_a])
    kind_b = _kind(data[col_b])

    if kind_a == "numeric" and kind_b == "numeric":
        return numeric_vs_numeric(data, col_a, col_b)
    if kind_a == "numeric" and kind_b == "categorical":
        return numeric_vs_categorical(data, col_a, col_b)
    if kind_a == "categorical" and kind_b == "numeric":
        return numeric_vs_categorical(data, col_b, col_a)
    if kind_a == "categorical" and kind_b == "categorical":
        return categorical_vs_categorical(data, col_a, col_b)
    if "datetime" in (kind_a, kind_b) and "numeric" in (kind_a, kind_b):
        date_col = col_a if kind_a == "datetime" else col_b
        num_col = col_b if kind_a == "datetime" else col_a
        return datetime_vs_numeric(data, date_col, num_col)
    if "datetime" in (kind_a, kind_b) and "categorical" in (kind_a, kind_b):
        return {
            "date": col_a if kind_a == "datetime" else col_b,
            "category": col_b if kind_a == "datetime" else col_a,
            "n": int(data[[col_a, col_b]].dropna().shape[0]),
            "recommendation": "Count categories over time with a line or bar chart.",
        }
    return {
        "x": col_a,
        "y": col_b,
        "n": 0,
        "recommendation": "No supported bivariate analysis for this column-type combination.",
    }
