"""
Data models for the ingestion module.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class LoadResult:
    """
    Result of loading a file.

    Attributes:
        df: The loaded DataFrame, or None if loading failed.
        warnings: Non-fatal issues detected during loading.
        errors: Fatal errors that prevented loading.
        file_meta: Metadata about the source file.
    """
    df: Optional[pd.DataFrame] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    file_meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        """Whether the file was loaded successfully."""
        return self.df is not None and len(self.errors) == 0
