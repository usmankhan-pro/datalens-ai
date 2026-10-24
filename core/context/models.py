"""User context data models for goal-aware workflows in DataLens AI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UserContext:
    """
    User context describing analytical intent and business environment.

    Attributes:
        goal: Purpose of data ingestion ('reporting', 'ml', 'business_analysis', 'research', 'other').
        target_column: Optional target feature for ML models or primary KPI for reporting.
        audience: Intended consumer ('Executive Leadership', 'Data Science Team', 'Operations', 'Research', 'General').
        domain: Detected industry/domain (e.g. 'Finance', 'Healthcare', 'E-Commerce', 'Marketing', 'HR/People', 'General').
        domain_confidence: Confidence score of rule-based domain detection (0.0 to 1.0).
        user_confirmed_domain: Whether the user explicitly accepted or manually selected the domain.
    """
    goal: str = "business_analysis"
    target_column: Optional[str] = None
    audience: str = "General"
    domain: str = "General"
    domain_confidence: float = 0.0
    user_confirmed_domain: bool = False

    def is_ml_goal(self) -> bool:
        """Check if analytical goal is Machine Learning."""
        return self.goal.lower() in ("ml", "machine_learning")

    def is_reporting_goal(self) -> bool:
        """Check if analytical goal is Executive or Operational Reporting."""
        return self.goal.lower() in ("reporting", "kpi_reporting")
