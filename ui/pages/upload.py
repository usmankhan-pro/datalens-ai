"""
Data Upload page — file upload, validation, and dataset loading.

Supports CSV, XLSX, XLS, JSON with auto-detection of encoding,
delimiter, and multi-sheet Excel files.
"""

import streamlit as st


def _format_file_size(size_bytes: int) -> str:
    """Format bytes into a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _render_upload_zone() -> None:
    """Render the file upload zone."""
    st.markdown(
        """
        <div class="upload-zone" style="margin-bottom: 1.5rem;">
            <div style="font-size: 3rem; margin-bottom: 0.5rem;">📁</div>
            <div style="font-size: 1.2rem; font-weight: 600;">
                Drag and drop your file here
            </div>
            <div style="font-size: 0.875rem; color: var(--text-muted); margin-top: 0.5rem;">
                Supports CSV, XLSX, XLS, JSON — up to 200 MB
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["csv", "xlsx", "xls", "json"],
        key="file_uploader",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        _process_uploaded_file(uploaded_file)


def _process_uploaded_file(uploaded_file) -> None:
    """Process the uploaded file through the ingestion pipeline."""
    from core.ingestion import load_file, get_sheet_names
    from core.utils.state import set_bundle, DatasetBundle, FileMeta

    filename = uploaded_file.name
    file_content = uploaded_file.getvalue()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Sheet selector for Excel
    sheet_name = None
    if ext in ("xlsx", "xls"):
        sheets = get_sheet_names(file_content, filename)
        if sheets and len(sheets) > 1:
            sheet_name = st.selectbox(
                "Select sheet to load:",
                options=sheets,
                key="sheet_selector",
            )

    # Load file
    with st.spinner(f"Loading {filename}..."):
        result = load_file(
            file_content=file_content,
            filename=filename,
            sheet_name=sheet_name,
        )

    if result.success:
        # Store in session state
        meta = FileMeta(
            name=filename,
            size_bytes=result.file_meta.get("size_bytes", len(file_content)),
            rows=result.file_meta.get("rows", len(result.df)),
            cols=result.file_meta.get("cols", len(result.df.columns)),
            extension=f".{ext}",
            encoding=result.file_meta.get("encoding"),
            delimiter=result.file_meta.get("delimiter"),
            sheet_name=result.file_meta.get("sheet_name"),
        )

        bundle = DatasetBundle(
            original_df=result.df.copy(),
            working_df=result.df.copy(),
            file_meta=meta,
            load_warnings=result.warnings,
        )
        set_bundle(bundle)
        st.rerun()
    else:
        # Show errors
        for error in result.errors:
            st.error(f"❌ {error}")

        # Show any warnings too
        for warning in result.warnings:
            st.warning(f"⚠️ {warning}")


def _render_loaded_state() -> None:
    """Render the post-upload state with file info and preview."""
    from core.utils.state import get_bundle, clear_bundle

    bundle = get_bundle()
    if bundle is None:
        return

    meta = bundle.file_meta

    # Success header
    st.markdown(
        '<div class="animate-fade-in">',
        unsafe_allow_html=True,
    )

    label = "Synthetic Demo Dataset" if bundle.is_demo else meta.name
    st.success(f"✅ Dataset loaded successfully: **{label}**")

    # File metadata cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{meta.name}</div>
                <div class="metric-label">File Name</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{_format_file_size(meta.size_bytes)}</div>
                <div class="metric-label">File Size</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{meta.rows:,}</div>
                <div class="metric-label">Rows</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value">{meta.cols}</div>
                <div class="metric-label">Columns</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Warnings
    if bundle.load_warnings:
        with st.expander(f"⚠️ Warnings ({len(bundle.load_warnings)})", expanded=True):
            for w in bundle.load_warnings:
                st.warning(w)

    # Data preview
    st.subheader("📋 Data Preview")
    st.caption(f"Showing first 100 of {meta.rows:,} rows")
    st.dataframe(
        bundle.original_df.head(100),
        use_container_width=True,
        height=400,
    )

    # Column info
    with st.expander("📊 Column Information"):
        col_info = []
        for col in bundle.original_df.columns:
            series = bundle.original_df[col]
            col_info.append({
                "Column": col,
                "Type": str(series.dtype),
                "Non-Null": f"{series.notna().sum():,}",
                "Missing": f"{series.isna().sum():,}",
                "Missing %": f"{series.isna().mean() * 100:.1f}%",
                "Unique": f"{series.nunique():,}",
            })
        st.dataframe(col_info, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Remove / Re-upload
    col_remove, col_spacer = st.columns([1, 3])
    with col_remove:
        if st.button(
            "🗑️  Remove & Re-upload",
            type="secondary",
            use_container_width=True,
            key="remove_dataset_btn",
        ):
            clear_bundle()
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def page() -> None:
    """Render the Data Upload page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("📤 Data Upload")
    st.markdown("---")

    from core.utils.state import has_dataset

    if has_dataset():
        _render_loaded_state()
    else:
        _render_upload_zone()

        # Divider + Demo option
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### Or try with sample data")
        if st.button(
            "🎲  Load Demo Dataset",
            key="upload_demo_btn",
            use_container_width=False,
        ):
            from ui.pages.dashboard import _load_demo
            from ui.pages.registry import get_page_registry

            _load_demo()
            st.switch_page(get_page_registry()["dashboard"])

    st.markdown("</div>", unsafe_allow_html=True)
