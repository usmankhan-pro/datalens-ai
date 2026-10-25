"""Audit-trail record types for cleaning operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class CleaningRecord:
    """A single entry in the cleaning audit trail."""

    step: str
    column: str
    operation: str
    rows_affected: int
    parameters: dict[str, Any] = field(default_factory=dict)
    before_stats: dict[str, Any] = field(default_factory=dict)
    after_stats: dict[str, Any] = field(default_factory=dict)
    succeeded: bool = True
    warning: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "column": self.column,
            "operation": self.operation,
            "rows_affected": self.rows_affected,
            "parameters": self.parameters,
            "before_stats": self.before_stats,
            "after_stats": self.after_stats,
            "succeeded": self.succeeded,
            "warning": self.warning,
            "timestamp": self.timestamp,
        }


@dataclass
class CleaningResult:
    """Result of a cleaning pipeline run."""

    cleaned_data: Any  # pd.DataFrame
    records: list[CleaningRecord] = field(default_factory=list)
    source_immutable: bool = True

    @property
    def success(self) -> bool:
        return all(r.succeeded for r in self.records)

    @property
    def n_operations(self) -> int:
        return len(self.records)

    def to_dict_list(self) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self.records]
