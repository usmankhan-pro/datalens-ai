"""Quality-analysis package for DataLens AI."""

from core.quality.issues import detect_issues
from core.quality.score import analyze_quality

__all__ = ["analyze_quality", "detect_issues"]