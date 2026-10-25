"""Formatting utilities for displaying numbers, percentages, and byte sizes."""

from __future__ import annotations

from typing import Any


def format_pct(value: float, decimals: int = 1) -> str:
    """Format a proportion (0-1) or percentage (0-100) as a string."""
    if value is None:
        return "n/a"
    return f"{value:.{decimals}f}%"


def format_count(value: int | float) -> str:
    """Format a count with thousands separators."""
    if value is None:
        return "n/a"
    return f"{int(value):,}"


def format_bytes(num_bytes: int | float) -> str:
    """Convert bytes to a human-readable string."""
    if num_bytes is None:
        return "n/a"
    num_bytes = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"


def format_score(score: float | None) -> str:
    """Format a quality score as 0-100 with one decimal."""
    if score is None:
        return "n/a"
    return f"{score:.1f} / 100"


def format_number(value: float | int | None, decimals: int = 2) -> str:
    """Format a number with thousands separators and fixed decimals."""
    if value is None:
        return "n/a"
    return f"{float(value):,.{decimals}f}"


def format_column_list(columns: list[Any], max_display: int = 10) -> str:
    """Format a list of column names for display."""
    if not columns:
        return "None"
    if len(columns) <= max_display:
        return ", ".join(str(c) for c in columns)
    return ", ".join(str(c) for c in columns[:max_display]) + f" ... (+{len(columns) - max_display} more)"
