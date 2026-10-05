"""Anomaly detection utilities for numeric and time-series data."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


class BaseDetector:
    """Base class for anomaly detectors."""

    method_name = "base"

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    def fit(self, values: Iterable[float]):
        """Fit the detector to a set of values and return self."""
        self._values = pd.Series(list(values), dtype=float)
        return self

    def detect(self, values: Iterable[float], column_name: Optional[str] = None):
        """Return a list of anomaly records for the provided values."""
        series = pd.Series(list(values), dtype=float).dropna().reset_index(drop=True)
        if series.empty:
            return []
        return self._detect_series(series, column_name=column_name)

    def _detect_series(self, series: pd.Series, column_name: Optional[str] = None):
        return []


def _prepare_numeric_series(values: Any) -> pd.Series:
    if isinstance(values, pd.Series):
        series = values.copy()
    else:
        series = pd.Series(values)
    numeric = pd.to_numeric(series, errors="coerce").dropna()
    return numeric.reset_index(drop=True)


class IQRDetector(BaseDetector):
    """Detect outliers using the IQR fence rule."""

    method_name = "iqr"

    def __init__(self, threshold: float = 1.5):
        super().__init__(threshold=threshold)

    def _detect_series(self, series: pd.Series, column_name: Optional[str] = None):
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - self.threshold * iqr
        upper = q3 + self.threshold * iqr

        anomalies = []
        for idx, value in series.items():
            if value < lower:
                direction = "low"
                score = abs((value - lower) / max(iqr, 1e-9))
            elif value > upper:
                direction = "high"
                score = abs((value - upper) / max(iqr, 1e-9))
            else:
                continue
            anomalies.append(
                {
                    "index": idx,
                    "column": column_name,
                    "value": float(value),
                    "score": float(score),
                    "method": self.method_name,
                    "direction": direction,
                    "message": "Potential anomaly detected.",
                }
            )
        return anomalies


class ZScoreDetector(BaseDetector):
    """Detect anomalies using z-scores."""

    method_name = "z"

    def __init__(self, threshold: float = 3.0):
        super().__init__(threshold=threshold)

    def _detect_series(self, series: pd.Series, column_name: Optional[str] = None):
        mean = series.mean()
        std = series.std(ddof=0)
        if std == 0 or pd.isna(std):
            return []

        anomalies = []
        for idx, value in series.items():
            z_score = abs((value - mean) / std)
            if z_score > self.threshold:
                direction = "high" if value > mean else "low"
                anomalies.append(
                    {
                        "index": idx,
                        "column": column_name,
                        "value": float(value),
                        "score": float(z_score),
                        "method": self.method_name,
                        "direction": direction,
                        "message": "Potential anomaly detected.",
                    }
                )
        return anomalies


class ModifiedZScoreDetector(BaseDetector):
    """Detect anomalies using the median-based modified z-score."""

    method_name = "modified_z"

    def __init__(self, threshold: float = 3.5):
        super().__init__(threshold=threshold)

    def _detect_series(self, series: pd.Series, column_name: Optional[str] = None):
        median = series.median()
        mad = (series - median).abs().median()
        if mad == 0 or pd.isna(mad):
            return []

        anomalies = []
        for idx, value in series.items():
            modified_z = 0.6745 * (value - median) / mad
            if abs(modified_z) > self.threshold:
                direction = "high" if value > median else "low"
                anomalies.append(
                    {
                        "index": idx,
                        "column": column_name,
                        "value": float(value),
                        "score": float(abs(modified_z)),
                        "method": self.method_name,
                        "direction": direction,
                        "message": "Potential anomaly detected.",
                    }
                )
        return anomalies


class RollingDetector(BaseDetector):
    """Detect time-series anomalies using rolling z-scores."""

    method_name = "rolling"

    def __init__(self, window: int = 7, threshold: float = 3.0):
        self.window = window
        super().__init__(threshold=threshold)

    def detect(self, values: Iterable[float], column_name: Optional[str] = None):
        series = _prepare_numeric_series(values)
        if series.empty:
            return []

        rolling_mean = series.rolling(window=self.window, min_periods=max(3, self.window // 2)).mean()
        rolling_std = series.rolling(window=self.window, min_periods=max(3, self.window // 2)).std(ddof=0)
        anomalies = []
        for idx, value in series.items():
            mean = rolling_mean.iloc[idx]
            std = rolling_std.iloc[idx]
            if pd.isna(mean) or pd.isna(std) or std == 0:
                continue
            z_score = abs((value - mean) / std)
            if z_score > self.threshold:
                direction = "high" if value > mean else "low"
                anomalies.append(
                    {
                        "index": idx,
                        "column": column_name,
                        "value": float(value),
                        "score": float(z_score),
                        "method": self.method_name,
                        "direction": direction,
                        "message": "Potential anomaly detected.",
                    }
                )
        return anomalies


def detect_anomalies(df: Any, method: str = "iqr", column: Optional[str] = None, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
    """Return anomaly records for a DataFrame or Series."""
    if isinstance(df, pd.Series):
        series = _prepare_numeric_series(df)
        detector = _build_detector(method=method, threshold=threshold)
        return detector.detect(series, column_name=column)

    if isinstance(df, pd.DataFrame):
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if column is not None:
            numeric_cols = [column] if column in df.columns else []
        detector = _build_detector(method=method, threshold=threshold)
        anomalies = []
        for col in numeric_cols:
            series = _prepare_numeric_series(df[col])
            anomalies.extend(detector.detect(series, column_name=col))
        return anomalies

    return []


def _build_detector(method: str, threshold: Optional[float] = None) -> BaseDetector:
    method_name = (method or "iqr").lower()
    if method_name == "iqr":
        return IQRDetector(threshold=1.5 if threshold is None else threshold)
    if method_name in {"z", "zscore"}:
        return ZScoreDetector(threshold=3.0 if threshold is None else threshold)
    if method_name in {"modified_z", "modifiedz", "modified-z"}:
        return ModifiedZScoreDetector(threshold=3.5 if threshold is None else threshold)
    if method_name in {"rolling", "rolling_z", "rolling-z"}:
        return RollingDetector(window=7, threshold=3.0 if threshold is None else threshold)
    return IQRDetector(threshold=1.5 if threshold is None else threshold)


__all__ = [
    "BaseDetector",
    "IQRDetector",
    "ZScoreDetector",
    "ModifiedZScoreDetector",
    "RollingDetector",
    "detect_anomalies",
]
