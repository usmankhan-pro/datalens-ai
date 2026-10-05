"""
DatasetBundle and session state management for DataLens AI.

Manages the central data container stored in Streamlit's session state.
The original_df is IMMUTABLE after load. All modifications work on working_df.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import pandas as pd
import hashlib


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


@dataclass
class TransformRecord:
    """Record of a single cleaning operation applied to the dataset."""
    timestamp: str
    operation: str
    columns: List[str]
    params: Dict[str, Any]
    rows_affected: int


@dataclass
class DatasetBundle:
    """
    Central data container for a loaded dataset.

    Attributes:
        original_df: The original uploaded DataFrame - NEVER modified after load.
        working_df: Mutable copy used for cleaning operations.
        file_meta: Metadata about the source file.
        profile: Column and dataset profile (populated in Phase 2).
        quality_result: Quality scores and issues (populated in Phase 2).
        transformation_history: Audit log of all cleaning operations applied.
        load_warnings: Warnings generated during data ingestion.
        is_demo: Whether this is the synthetic demo dataset.
    """
    original_df: pd.DataFrame
    working_df: pd.DataFrame
    file_meta: FileMeta
    profile: Optional[Any] = None
    quality_result: Optional[Any] = None
    transformation_history: List[TransformRecord] = field(default_factory=list)
    load_warnings: List[str] = field(default_factory=list)
    is_demo: bool = False


_SESSION_KEY = "datalens_dataset_bundle"
_THEME_KEY = "datalens_theme"


def get_bundle() -> Optional["DatasetBundle"]:
    """Retrieve the DatasetBundle from session state, or None if not loaded."""
    import streamlit as st
    return st.session_state.get(_SESSION_KEY, None)


def set_bundle(bundle: "DatasetBundle") -> None:
    """Store a DatasetBundle in session state."""
    import streamlit as st
    st.session_state[_SESSION_KEY] = bundle


def clear_bundle() -> None:
    """Remove the DatasetBundle from session state."""
    import streamlit as st
    if _SESSION_KEY in st.session_state:
        del st.session_state[_SESSION_KEY]


def has_dataset() -> bool:
    """Check whether a dataset is currently loaded."""
    return get_bundle() is not None


def get_theme() -> str:
    """Get the current theme ('dark' or 'light'). Defaults to 'dark'."""
    import streamlit as st
    return st.session_state.get(_THEME_KEY, "dark")


def set_theme(theme: str) -> None:
    """Set the current theme ('dark' or 'light')."""
    import streamlit as st
    st.session_state[_THEME_KEY] = theme


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

    Args:
        df: DataFrame to hash.

    Returns:
        MD5 hex digest string.
    """
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
