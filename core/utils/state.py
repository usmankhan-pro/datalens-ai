"""DatasetBundle and session state management for DataLens AI.

Manages the central data container stored in Streamlit's session state.
The original_df is IMMUTABLE after load. All modifications work on working_df.
Includes versioned in-memory copies for undo support and audit logging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import pandas as pd


@dataclass
class FileMeta:
    """Metadata about the uploaded file."""
    name: str
    size_bytes: int
    rows: int
    cols: int
    extension: str
    encoding: Optional[str] = None
    delimiter: Optional[str] = None
    sheet_name: Optional[str] = None
    header_row: Optional[int] = 0


@dataclass
class TransformRecord:
    """Record of a single cleaning operation applied to the dataset."""
    timestamp: str
    operation: str
    columns: List[str]
    params: Dict[str, Any]
    rows_affected: int
    stage: str = "cleaning"
    risk: str = "safe"


@dataclass
class DatasetBundle:
    """
    Central data container for a loaded dataset.

    Attributes:
        original_df: The original uploaded DataFrame - NEVER modified after load.
        working_df: Mutable copy used for cleaning operations.
        file_meta: Metadata about the source file.
        profile: Column and dataset profile.
        quality_result: Quality scores and issues.
        transformation_history: Audit log of all cleaning operations applied.
        history_stack: In-memory stack of previous working_df snapshots for undo.
        user_context: Goal-aware user context (reporting, ML, etc.).
        action_plan: Ordered recommendations plan.
        readiness_verdict: Final pass/warn/fail checklist.
        load_warnings: Warnings generated during data ingestion.
        is_demo: Whether this is the synthetic demo dataset.
    """
    original_df: pd.DataFrame
    working_df: pd.DataFrame
    file_meta: FileMeta
    profile: Optional[Any] = None
    quality_result: Optional[Any] = None
    transformation_history: List[TransformRecord] = field(default_factory=list)
    history_stack: List[pd.DataFrame] = field(default_factory=list)
    user_context: Optional[Any] = None
    action_plan: Optional[Any] = None
    readiness_verdict: Optional[Any] = None
    load_warnings: List[str] = field(default_factory=list)
    is_demo: bool = False

    def push_snapshot(self) -> None:
        """Push a copy of the current working_df to the in-memory undo stack."""
        if self.working_df is not None:
            # Keep stack depth reasonable (up to 20 steps)
            if len(self.history_stack) >= 20:
                self.history_stack.pop(0)
            self.history_stack.append(self.working_df.copy())

    def undo(self) -> bool:
        """Revert working_df to the previous snapshot in the history stack."""
        if not self.history_stack:
            return False
        self.working_df = self.history_stack.pop()
        if self.transformation_history:
            self.transformation_history.pop()
        return True

    def can_undo(self) -> bool:
        """Check if an undo snapshot is available."""
        return len(self.history_stack) > 0

    def reset_to_original(self) -> None:
        """Reset working_df back to the original unmodified dataset."""
        self.push_snapshot()
        self.working_df = self.original_df.copy()
        self.transformation_history.clear()


_SESSION_KEY = "datalens_dataset_bundle"
_THEME_KEY = "datalens_theme"


def get_bundle() -> Optional["DatasetBundle"]:
    """Retrieve the DatasetBundle from session state, or None if not loaded."""
    try:
        import streamlit as st
        return st.session_state.get(_SESSION_KEY, None)
    except Exception:
        return None


def set_bundle(bundle: "DatasetBundle") -> None:
    """Store a DatasetBundle in session state."""
    try:
        import streamlit as st
        st.session_state[_SESSION_KEY] = bundle
    except Exception:
        pass


def clear_bundle() -> None:
    """Remove the DatasetBundle from session state."""
    try:
        import streamlit as st
        if _SESSION_KEY in st.session_state:
            del st.session_state[_SESSION_KEY]
    except Exception:
        pass


def has_dataset() -> bool:
    """Check whether a dataset is currently loaded."""
    return get_bundle() is not None


def get_theme() -> str:
    """Get the current theme ('dark' or 'light'). Defaults to 'dark'."""
    try:
        import streamlit as st
        return st.session_state.get(_THEME_KEY, "dark")
    except Exception:
        return "dark"


def set_theme(theme: str) -> None:
    """Set the current theme ('dark' or 'light')."""
    try:
        import streamlit as st
        st.session_state[_THEME_KEY] = theme
    except Exception:
        pass


def toggle_theme() -> str:
    """Toggle between dark and light theme. Returns the new theme name."""
    current = get_theme()
    new_theme = "light" if current == "dark" else "dark"
    set_theme(new_theme)
    return new_theme


def compute_df_hash(df: pd.DataFrame) -> str:
    """
    Compute a deterministic hash of a DataFrame for cache keying.

    Uses shape + column names + dtypes + first/last rows for efficiency
    rather than hashing the entire frame.
    """
    if df is None:
        return ""
    hash_components = [
        str(df.shape),
        str(list(df.columns)),
        str(df.dtypes.tolist()),
    ]
    if len(df) > 0:
        hash_components.append(str(df.iloc[0].tolist()))
        hash_components.append(str(df.iloc[-1].tolist()))
    hash_str = "|".join(hash_components)
    return hashlib.md5(hash_str.encode()).hexdigest()
