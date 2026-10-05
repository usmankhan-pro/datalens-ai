"""KPI detection and calculation helpers."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


_REVENUE_ALIASES = ("revenue", "sales", "amount", "turnover")
_COST_ALIASES = ("cost", "expense", "expenses")
_PROFIT_ALIASES = ("profit", "gross_profit", "net_profit", "margin")
_ORDERS_ALIASES = ("orders", "transaction", "transactions", "order_count")
_CUSTOMER_ALIASES = ("customer", "customers", "client", "clients", "user", "users")
_MARKETING_ALIASES = ("marketing", "marketing_spend", "ad_spend", "spend")
_QUANTITY_ALIASES = ("quantity", "units", "qty")


def _normalize_name(name: str) -> str:
    return str(name).strip().lower().replace(" ", "_")


def _find_matching_column(df: pd.DataFrame, aliases: Iterable[str]) -> Optional[str]:
    alias_set = {_normalize_name(alias) for alias in aliases}
    for column in df.columns:
        normalized = _normalize_name(str(column))
        if normalized in alias_set:
            return str(column)
    for column in df.columns:
        normalized = _normalize_name(str(column))
        if any(alias in normalized for alias in alias_set):
            return str(column)
    return None


def _as_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").dropna()


def detect_kpis(df: pd.DataFrame, overrides: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Infer and calculate key business KPIs from a DataFrame."""
    if df is None or df.empty:
        return []

    overrides = overrides or {}
    resolved = dict(overrides)
    kpis: List[Dict[str, Any]] = []

    revenue_col = resolved.get("revenue") or _find_matching_column(df, _REVENUE_ALIASES)
    cost_col = resolved.get("cost") or _find_matching_column(df, _COST_ALIASES)
    profit_col = resolved.get("profit") or _find_matching_column(df, _PROFIT_ALIASES)
    orders_col = resolved.get("orders") or _find_matching_column(df, _ORDERS_ALIASES)
    customer_col = resolved.get("customers") or _find_matching_column(df, _CUSTOMER_ALIASES)
    marketing_col = resolved.get("marketing") or _find_matching_column(df, _MARKETING_ALIASES)
    quantity_col = resolved.get("quantity") or _find_matching_column(df, _QUANTITY_ALIASES)

    if revenue_col:
        total_revenue = float(_as_numeric(df[revenue_col]).sum())
        kpis.append({
            "name": "Total Revenue",
            "value": total_revenue,
            "unit": "currency",
            "source_col": revenue_col,
            "confidence": 0.9,
        })

    if cost_col:
        total_cost = float(_as_numeric(df[cost_col]).sum())
        kpis.append({
            "name": "Total Cost",
            "value": total_cost,
            "unit": "currency",
            "source_col": cost_col,
            "confidence": 0.9,
        })

    if profit_col:
        total_profit = float(_as_numeric(df[profit_col]).sum())
        kpis.append({
            "name": "Total Profit",
            "value": total_profit,
            "unit": "currency",
            "source_col": profit_col,
            "confidence": 0.9,
        })

    if orders_col and revenue_col:
        revenue = _as_numeric(df[revenue_col])
        orders = _as_numeric(df[orders_col])
        total_orders = float(orders.sum()) if not orders.empty else 0.0
        if total_orders > 0:
            kpis.append({
                "name": "Average Order Value",
                "value": float(revenue.sum() / total_orders),
                "unit": "currency",
                "source_cols": [revenue_col, orders_col],
                "confidence": 0.8,
            })

    if customer_col:
        unique_customers = float(df[customer_col].nunique())
        kpis.append({
            "name": "Unique Customers",
            "value": unique_customers,
            "unit": "count",
            "source_col": customer_col,
            "confidence": 0.8,
        })

    if revenue_col and profit_col:
        revenue_total = float(_as_numeric(df[revenue_col]).sum())
        profit_total = float(_as_numeric(df[profit_col]).sum())
        if revenue_total:
            kpis.append({
                "name": "Profit Margin",
                "value": float((profit_total / revenue_total) * 100.0),
                "unit": "percent",
                "source_cols": [revenue_col, profit_col],
                "confidence": 0.8,
            })

    if quantity_col:
        total_quantity = float(_as_numeric(df[quantity_col]).sum())
        kpis.append({
            "name": "Total Quantity",
            "value": total_quantity,
            "unit": "count",
            "source_col": quantity_col,
            "confidence": 0.7,
        })

    if marketing_col:
        marketing_spend = float(_as_numeric(df[marketing_col]).sum())
        kpis.append({
            "name": "Marketing Spend",
            "value": marketing_spend,
            "unit": "currency",
            "source_col": marketing_col,
            "confidence": 0.7,
        })

    return kpis


def compute_kpi_summary(df: pd.DataFrame, overrides: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Return a KPI summary dictionary with the detected metric list."""
    metrics = detect_kpis(df, overrides=overrides)
    return {"status": "ok" if metrics else "insufficient", "metrics": metrics}


__all__ = ["detect_kpis", "compute_kpi_summary"]
