"""Central configuration for DataLens AI.

Contains quality-score dimension weights, severity thresholds,
cleaning parameters, and resource limits.  All values are
product conventions, not scientific standards, and are
intentionally adjustable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityWeights:
    """Weights for the five quality dimensions (must sum to 100)."""

    completeness: int = 25
    validity: int = 25
    consistency: int = 20
    uniqueness: int = 15
    structural: int = 15

    def __post_init__(self) -> None:
        total = (
            self.completeness
            + self.validity
            + self.consistency
            + self.uniqueness
            + self.structural
        )
        if total != 100:
            raise ValueError(f"Quality weights must sum to 100, got {total}")


@dataclass(frozen=True)
class QualityThresholds:
    """Interpretation bands for the overall 0-100 quality score."""

    excellent: int = 85
    good: int = 70
    needs_improvement: int = 50
    # Below needs_improvement is "Poor"

    def label(self, score: float) -> str:
        if score >= self.excellent:
            return "Excellent"
        if score >= self.good:
            return "Good"
        if score >= self.needs_improvement:
            return "Needs Improvement"
        return "Poor"


@dataclass(frozen=True)
class MissingValueThresholds:
    """Severity thresholds for per-column missingness."""

    high: float = 50.0   # percent
    medium: float = 20.0  # percent
    low: float = 10.0     # percent


@dataclass(frozen=True)
class DuplicateThresholds:
    """Severity thresholds for duplicate-row percentage."""

    high: float = 10.0   # percent of rows
    medium: float = 5.0   # percent of rows


@dataclass(frozen=True)
class CardinalityThresholds:
    """High-cardinality detection for text columns."""

    min_rows: int = 10
    min_unique: int = 10
    ratio: float = 0.9   # unique / non-null rows


@dataclass(frozen=True)
class OutlierConfig:
    """Outlier detection parameters."""

    iqr_multiplier: float = 1.5
    z_score_threshold: float = 3.0


@dataclass(frozen=True)
class ResourceLimits:
    """Configurable resource limits for uploads and processing."""

    max_file_size_mb: int = 200
    max_rows: int = 1_000_000
    max_processing_seconds: int = 300


QUALITY_WEIGHTS = QualityWeights()
QUALITY_THRESHOLDS = QualityThresholds()
MISSING_THRESHOLDS = MissingValueThresholds()
DUPLICATE_THRESHOLDS = DuplicateThresholds()
CARDINALITY_THRESHOLDS = CardinalityThresholds()
OUTLIER_CONFIG = OutlierConfig()
RESOURCE_LIMITS = ResourceLimits()

# Placeholder values treated as missing when they appear in text columns.
MISSING_PLACEHOLDERS = frozenset(
    {"n/a", "na", "null", "none", "nan", "unknown", "missing", "-", "--", ""}
)

# Columns whose names suggest they are identifiers; statistical summaries
# are still computed but correlation inclusion is discouraged.
IDENTIFIER_NAME_HINTS = frozenset(
    {"id", "identifier", "key", "code", "number", "no", "index", "uid", "uuid"}
)

DEMO_DATASET_NAME = "Telco customer churn demo"


@dataclass(frozen=True)
class ScoreInterpretation:
    """Human-readable interpretation of a quality score."""

    label: str
    description: str
    recommendation: str


SCORE_INTERPRETATIONS: dict[str, ScoreInterpretation] = {
    "Excellent": ScoreInterpretation(
        label="Excellent",
        description=(
            "The dataset has very few quality issues. It is suitable for most "
            "analytical purposes without extensive cleaning."
        ),
        recommendation=(
            "Proceed directly to exploratory analysis. Consider a light review "
            "of any LOW-severity findings."
        ),
    ),
    "Good": ScoreInterpretation(
        label="Good",
        description=(
            "The dataset is generally sound but has some issues that should be "
            "reviewed before analysis."
        ),
        recommendation=(
            "Review MEDIUM and LOW findings. Apply targeted cleaning to the "
            "flagged columns before EDA."
        ),
    ),
    "Needs Improvement": ScoreInterpretation(
        label="Needs Improvement",
        description=(
            "The dataset has several quality issues that may affect analysis "
            "results if left unaddressed."
        ),
        recommendation=(
            "Prioritize HIGH and MEDIUM findings. Clean missing values, "
            "duplicates, and type issues before analysis."
        ),
    ),
    "Poor": ScoreInterpretation(
        label="Poor",
        description=(
            "The dataset has significant quality issues. Analysis results may "
            "be unreliable without substantial cleaning."
        ),
        recommendation=(
            "Address HIGH-severity findings first. Verify the data source and "
            "consider re-collecting if critical columns are largely empty or "
            "malformed."
        ),
    ),
}
