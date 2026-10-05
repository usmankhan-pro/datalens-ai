"""Data Explorer page — interactive data browsing with filters."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.utils.state import get_bundle, has_dataset


def filter_dataframe(
    df: pd.DataFrame,
    search_text: str = "",
    filter_column: str | None = None,
    filter_value: str | None = None,
    numeric_min: float | None = None,
    numeric_max: float | None = None,
) -> pd.DataFrame:
    """Apply text and numeric filters to a dataset for the explorer view."""
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    view = df.copy()

    if search_text:
        search = search_text.lower().strip()
        text_mask = view.astype(str).apply(
            lambda row: search in " ".join(row.astype(str).tolist()).lower(),
            axis=1,
        )
        view = view[text_mask]

    if filter_column and filter_column in view.columns:
        column_values = view[filter_column]
        if filter_value:
            view = view[column_values.astype(str).str.contains(str(filter_value), case=False, na=False)]
        if pd.api.types.is_numeric_dtype(column_values):
            if numeric_min is not None:
                view = view[column_values >= numeric_min]
            if numeric_max is not None:
                view = view[column_values <= numeric_max]

    return view


def page() -> None:
    """Render the Data Explorer page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🗂️ Data Explorer")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🗂️</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to explore and filter your data.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for exploration.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    source = st.radio("Dataset source", ["Working Data", "Original Data"], horizontal=True)
    df = bundle.working_df if source == "Working Data" else bundle.original_df

    st.subheader("Filters")
    search_text = st.text_input("Search text", placeholder="Type a keyword to find matching rows")
    filter_column = st.selectbox("Filter column", ["None", *df.columns.tolist()])
    filter_value = None
    numeric_min = None
    numeric_max = None

    if filter_column != "None":
        column = df[filter_column]
        if pd.api.types.is_numeric_dtype(column):
            numeric_min = st.number_input(f"Minimum {filter_column}", value=float(column.min()), step=1.0)
            numeric_max = st.number_input(f"Maximum {filter_column}", value=float(column.max()), step=1.0)
        else:
            filter_value = st.text_input(f"Contains in {filter_column}", placeholder="Filter text")

    filtered = filter_dataframe(
        df,
        search_text=search_text,
        filter_column=None if filter_column == "None" else filter_column,
        filter_value=filter_value,
        numeric_min=numeric_min,
        numeric_max=numeric_max,
    )

    st.caption(f"Showing {len(filtered):,} of {len(df):,} rows")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
