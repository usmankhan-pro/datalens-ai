"""
Metadata-only logging helper for DataLens AI.

PRIVACY RULE: Never log raw row values or DataFrame contents.
Only log metadata: shape, column names, timings, error types.
"""

import logging
import time
from typing import Any, Optional
import pandas as pd


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name, typically __name__ of the calling module.

    Returns:
        Configured Logger instance with console handler.
    """
    logger = logging.getLogger(f"datalens.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _sanitize_value(value: Any) -> Any:
    """
    Sanitize a value for safe logging.
    Refuses to log DataFrames or Series — logs metadata instead.
    """
    if isinstance(value, pd.DataFrame):
        return f"<DataFrame shape={value.shape} cols={list(value.columns)}>"
    if isinstance(value, pd.Series):
        return f"<Series name={value.name} len={len(value)}>"
    if isinstance(value, (list, tuple)) and len(value) > 20:
        return f"<{type(value).__name__} len={len(value)}>"
    return value


def log_metadata(logger: logging.Logger, message: str, **kwargs: Any) -> None:
    """
    Log metadata safely. DataFrame/Series values are automatically
    replaced with their shape/column metadata.

    Args:
        logger: Logger instance.
        message: Log message.
        **kwargs: Key-value pairs of metadata to include.
    """
    sanitized = {k: _sanitize_value(v) for k, v in kwargs.items()}
    parts = [f"{k}={v}" for k, v in sanitized.items()]
    logger.info(f"{message} | {' | '.join(parts)}" if parts else message)


def log_error(
    logger: logging.Logger,
    message: str,
    error: Optional[Exception] = None,
    **kwargs: Any,
) -> None:
    """
    Log an error safely with metadata.

    Args:
        logger: Logger instance.
        message: Error description.
        error: Optional exception instance.
        **kwargs: Additional metadata key-value pairs.
    """
    sanitized = {k: _sanitize_value(v) for k, v in kwargs.items()}
    parts = [f"{k}={v}" for k, v in sanitized.items()]
    error_type = type(error).__name__ if error else "Unknown"
    error_msg = str(error) if error else ""
    logger.error(
        f"{message} | error_type={error_type} | error_msg={error_msg}"
        + (f" | {' | '.join(parts)}" if parts else "")
    )


class TimingContext:
    """Context manager for timing operations and logging the duration."""

    def __init__(self, logger: logging.Logger, operation: str):
        self.logger = logger
        self.operation = operation
        self.start_time: float = 0.0
        self.duration: float = 0.0

    def __enter__(self) -> "TimingContext":
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.duration = time.time() - self.start_time
        log_metadata(
            self.logger,
            f"{self.operation} completed",
            duration_seconds=round(self.duration, 3),
        )
        return False
