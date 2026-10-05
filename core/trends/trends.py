"""Trend analysis helpers for time-series datasets."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


def _coerce_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")


def analyze_trends(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    freq: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a trend summary for a time series with graceful insufficient-data handling."""
    if df is None or df.empty:
        return {"status": "insufficient", "reason": "Insufficient data for trend analysis."}
    if date_col not in df.columns or value_col not in df.columns:
        return {"status": "insufficient", "reason": "Insufficient data for trend analysis: required columns are missing."}

    work = df[[date_col, value_col]].copy()
    work[date_col] = _coerce_datetime(work[date_col])
    work = work.dropna(subset=[date_col, value_col]).sort_values(date_col)
    if work.empty or len(work) < 2:
        return {"status": "insufficient", "reason": "Insufficient data for trend analysis because the time series is too short."}

    numeric = pd.to_numeric(work[value_col], errors="coerce")
    work[value_col] = numeric
    work = work.dropna(subset=[value_col])
    if work.empty or len(work) < 2:
        return {"status": "insufficient", "reason": "Insufficient data for trend analysis because the value column has no usable numeric data."}

    periods = work.set_index(date_col)[value_col]
    if freq is None:
        freq = "M" if len(periods) > 30 else "D"
    aggregated = periods.resample(freq).mean().dropna()
    if len(aggregated) < 2:
        return {"status": "insufficient", "reason": "Insufficient data for trend analysis because fewer than two periods are available."}

    x = np.arange(len(aggregated))
    slope = np.polyfit(x, aggregated.to_numpy(), 1)[0]
    first_value = float(aggregated.iloc[0])
    last_value = float(aggregated.iloc[-1])
    pct_change = 0.0 if abs(first_value) < 1e-9 else ((last_value - first_value) / abs(first_value)) * 100.0
    direction = "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable"
    peak = aggregated.idxmax()
    trough = aggregated.idxmin()

    result = {
        "status": "ok",
        "date_col": date_col,
        "value_col": value_col,
        "frequency": freq,
        "direction": direction,
        "slope": float(slope),
        "percent_change": float(pct_change),
        "start_value": float(first_value),
        "end_value": float(last_value),
        "peak_period": str(peak),
        "trough_period": str(trough),
        "summary": (
            f"The series shows a {direction} trend with a total change of {pct_change:.2f}% "
            f"from {first_value:.2f} to {last_value:.2f}."
        ),
    }
    return result


def compute_trend_summary(df: pd.DataFrame, date_col: str, value_col: str, freq: Optional[str] = None) -> Dict[str, Any]:
    """Compatibility wrapper for trend analysis."""
    return analyze_trends(df, date_col, value_col, freq=freq)


__all__ = ["analyze_trends", "compute_trend_summary"]
