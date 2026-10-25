"""Shared, session-scoped DataFlow Analytics workspace state."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pandas as pd
import streamlit as st

from src.cleaning.cleaning_pipeline import CleaningPipeline


def initialize_workspace(
    data: pd.DataFrame,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Start a workspace while preserving independent copies of input data."""
    pipeline = CleaningPipeline(data)
    st.session_state["data"] = pipeline.source
    st.session_state["original_data"] = pipeline.source
    st.session_state["cleaning_pipeline"] = pipeline
    st.session_state["cleaned_data"] = pipeline.working
    st.session_state["cleaning_log"] = []
    st.session_state["source"] = source
    st.session_state["dataset_metadata"] = dict(metadata or {})
    st.session_state["workspace_id"] = uuid4().hex
    st.session_state["workspace_revision"] = 0
    st.session_state["analysis_cache"] = {}
    st.session_state.pop("cleaning_preview", None)


def current_pipeline() -> CleaningPipeline | None:
    """Return the pipeline if a dataset has been loaded."""
    pipeline = st.session_state.get("cleaning_pipeline")
    return pipeline if isinstance(pipeline, CleaningPipeline) else None


def current_data() -> pd.DataFrame | None:
    """Return the current working dataset."""
    pipeline = current_pipeline()
    return pipeline.working if pipeline else None


def mark_workspace_changed() -> None:
    """Invalidate analyses and selections after an approved data change."""
    pipeline = current_pipeline()
    if pipeline is None:
        return
    st.session_state["workspace_revision"] = (
        int(st.session_state.get("workspace_revision", 0)) + 1
    )
    st.session_state["cleaned_data"] = pipeline.working
    st.session_state["cleaning_log"] = [record.to_dict() for record in pipeline.records]
    st.session_state["analysis_cache"] = {}
    st.session_state.pop("cleaning_preview", None)


def workspace_widget_key(name: str) -> str:
    """Scope input selections to a particular dataset so replacements cannot stale them."""
    workspace_id = st.session_state.get("workspace_id", "empty")
    return f"{name}_{workspace_id}"
