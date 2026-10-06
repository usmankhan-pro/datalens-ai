"""Data Profile page — column profiling and type inference."""

import pandas as pd
import streamlit as st

from core.profiling import profile_dataframe
from core.utils.state import get_bundle, has_dataset, set_bundle


def page() -> None:
    """Render the Data Profile page with column-level summaries."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🔬 Data Profile")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🔬</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to view its profile and column analysis.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available to profile.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    profile = bundle.profile or profile_dataframe(bundle.original_df)
    bundle.profile = profile
    set_bundle(bundle)

    st.subheader("Dataset Summary")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Rows", f"{profile['rows']:,}")
    with col2:
        st.metric("Columns", profile['cols'])
    with col3:
        st.metric("Missing Cells", f"{profile['total_missing_cells']:,}")
    with col4:
        st.metric("Duplicate Rows", f"{profile['duplicate_rows']:,}")

    type_counts = profile["type_counts"]
    type_df = pd.DataFrame(
        {
            "Type": list(type_counts.keys()),
            "Count": [int(type_counts[k]) for k in type_counts],
        }
    )
    type_df = type_df[type_df["Count"] > 0]
    if not type_df.empty:
        st.subheader("Type Distribution")
        st.bar_chart(type_df.set_index("Type"))

    st.subheader("Column Profile")
    column_rows = []
    for item in profile.get("column_profiles", list(profile.get("columns", {}).values())):
        column_rows.append(
            {
                "Column": item["column"],
                "Type": item["inferred_type"],
                "Dtype": item["dtype"],
                "Missing": item["missing_count"],
                "Missing %": round(item["missing_pct"], 2),
                "Unique": item["unique_count"],
                "Constant": item["constant"],
                "ID": item["is_id"],
            }
        )
    st.dataframe(pd.DataFrame(column_rows), width="stretch", hide_index=True)

    st.markdown("</div>", unsafe_allow_html=True)
