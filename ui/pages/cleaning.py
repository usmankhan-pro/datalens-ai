"""Data Cleaning page — 8-stage interactive cleaning workspace with undo and auto-clean."""

import json
from datetime import datetime
import pandas as pd
import streamlit as st

from core.cleaning import (
    CLEANING_STAGES,
    OPERATION_SPECS,
    apply_operation,
    auto_clean_safe_steps,
    clean_validate_dataset,
    preview_operation,
)
from core.export.script_generator import generate_cleaning_script
from core.utils.state import (
    DatasetBundle,
    TransformRecord,
    get_bundle,
    has_dataset,
    set_bundle,
)


def _render_top_toolbar(bundle: DatasetBundle) -> None:
    """Render the primary action toolbar: Auto-clean, Undo, and Reset."""
    c1, c2, c3, c4 = st.columns([2.5, 1.2, 1.2, 2.5])

    with c1:
        if st.button(
            "🚀 Auto-clean (Safe Steps Only)",
            type="primary",
            use_container_width=True,
            key="clean_auto_clean_btn",
            help="Executes safe structural, type, placeholder, text, and duplicate cleanup without user intervention.",
        ):
            bundle.push_snapshot()
            cleaned_df, records = auto_clean_safe_steps(bundle.working_df)
            bundle.working_df = cleaned_df
            bundle.transformation_history.extend(records)
            set_bundle(bundle)
            st.success(f"Auto-clean completed! {len(records)} safe operations executed.")
            st.rerun()

    with c2:
        can_undo = bundle.can_undo()
        if st.button(
            "↩️ Undo Step",
            disabled=not can_undo,
            use_container_width=True,
            key="clean_undo_btn",
            help="Revert the dataset to the state prior to the last applied operation.",
        ):
            if bundle.undo():
                set_bundle(bundle)
                st.info("Reverted to previous working copy.")
                st.rerun()

    with c3:
        if st.button(
            "🔄 Reset All",
            use_container_width=True,
            key="clean_reset_btn",
            help="Reset the working dataset back to the original unmodified state.",
        ):
            bundle.reset_to_original()
            set_bundle(bundle)
            st.warning("Working dataset reset to original uploaded data.")
            st.rerun()

    with c4:
        # Mini metrics
        total_cells = bundle.working_df.size
        missing_cells = int(bundle.working_df.isna().sum().sum())
        missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
        dups = int(bundle.working_df.duplicated().sum())

        st.caption(
            f"**Current shape:** {len(bundle.working_df):,} rows × {len(bundle.working_df.columns)} cols | "
            f"**Missing:** {missing_pct:.1f}% | **Duplicates:** {dups:,}"
        )


def _apply_step(
    bundle: DatasetBundle,
    operation: str,
    params: dict,
    stage: str,
    risk: str,
    columns: list,
) -> None:
    """Helper to apply a step, push snapshot for undo, and record in audit log."""
    bundle.push_snapshot()
    res = apply_operation(bundle.working_df, operation, params)
    bundle.working_df = res["df"]
    bundle.transformation_history.append(
        TransformRecord(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            operation=operation,
            columns=columns,
            params=params,
            rows_affected=res["rows_affected"],
            stage=stage,
            risk=risk,
        )
    )
    set_bundle(bundle)
    st.success(f"Applied '{operation}': {res['rows_affected']} rows/cells affected.")
    st.rerun()


def _render_stage_structure(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 1: Structure (empty rows/cols, snake_case headers)."""
    st.markdown("#### 1. Structure Cleanup")
    st.caption("Standardize column naming and remove completely empty rows or columns.")

    col1, col2, col3 = st.columns(3)

    # 1. Drop Empty Rows
    with col1:
        st.markdown("**Drop Empty Rows**")
        how_choice = st.selectbox("Drop criteria:", ["all", "any"], key="struct_drop_rows_how")
        prev = preview_operation(df, "drop_empty_rows", {"how": how_choice})
        st.caption(f"Rows affected: **{prev['rows_affected']:,}**")
        if st.button("Apply Drop Empty Rows", key="btn_drop_empty_rows"):
            _apply_step(bundle, "drop_empty_rows", {"how": how_choice}, "structure", "safe", list(df.columns))

    # 2. Drop Empty Columns
    with col2:
        st.markdown("**Drop Empty Columns**")
        empty_cols = [c for c in df.columns if df[c].isna().all()]
        st.caption(f"Empty columns found: **{len(empty_cols)}** ({', '.join(empty_cols) if empty_cols else 'None'})")
        if st.button("Apply Drop Empty Columns", disabled=len(empty_cols) == 0, key="btn_drop_empty_cols"):
            _apply_step(bundle, "drop_empty_columns", {}, "structure", "safe", empty_cols)

    # 3. Snake Case Names
    with col3:
        st.markdown("**Snake Case Column Names**")
        st.caption("Convert spaces, dashes, and CamelCase to lowercase `snake_case`.")
        if st.button("Apply Snake Case Names", key="btn_snake_case"):
            _apply_step(bundle, "snake_case_columns", {}, "structure", "safe", list(df.columns))


def _render_stage_types(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 2: Types (numeric strings, dates, booleans)."""
    st.markdown("#### 2. Type Standardization")
    st.caption("Detect formatted numeric text, date strings, and booleans and cast to native types.")

    col1, col2, col3 = st.columns(3)

    # 1. Numeric Text
    with col1:
        st.markdown("**Clean Numeric Text**")
        st.caption("Strips $, %, commas, (parentheses) from currency/percentage strings.")
        str_cols = [c for c in df.columns if df[c].dtype == "object" or pd.api.types.is_string_dtype(df[c])]
        sel_num_cols = st.multiselect("Columns (leave blank for all string cols):", str_cols, key="types_num_cols")
        if st.button("Convert to Numeric", key="btn_conv_numeric"):
            _apply_step(bundle, "convert_numeric_text", {"columns": sel_num_cols or None}, "types", "safe", sel_num_cols)

    # 2. Parse Dates
    with col2:
        st.markdown("**Parse Dates**")
        st.caption("Parse date/time strings to datetime format.")
        sel_date_cols = st.multiselect("Select Date Columns:", str_cols, key="types_date_cols")
        if st.button("Parse Dates", disabled=len(sel_date_cols) == 0, key="btn_parse_dates"):
            _apply_step(bundle, "parse_dates", {"columns": sel_date_cols}, "types", "safe", sel_date_cols)

    # 3. Convert Booleans
    with col3:
        st.markdown("**Convert Booleans**")
        st.caption("Cast yes/no, true/false, 1/0 text into boolean flags.")
        sel_bool_cols = st.multiselect("Select Boolean Columns:", str_cols, key="types_bool_cols")
        if st.button("Convert Booleans", disabled=len(sel_bool_cols) == 0, key="btn_conv_booleans"):
            _apply_step(bundle, "convert_booleans", {"columns": sel_bool_cols}, "types", "safe", sel_bool_cols)


def _render_stage_text(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 3: Text (trim, case, variants)."""
    st.markdown("#### 3. Text Standardization")
    st.caption("Clean up string columns: strip whitespace, normalize casing, or harmonize variants.")

    str_cols = [c for c in df.columns if df[c].dtype == "object" or pd.api.types.is_string_dtype(df[c])]
    if not str_cols:
        st.info("No text columns available in the current dataset.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Trim & Casing**")
        target_cols = st.multiselect("Select text columns (empty = all):", str_cols, key="text_cols_sel")
        case_opt = st.selectbox("Case normalization:", ["preserve", "lower", "upper", "title"], key="text_case_opt")
        strip_opt = st.checkbox("Strip leading/trailing spaces", value=True, key="text_strip_opt")
        collapse_opt = st.checkbox("Collapse multiple internal spaces", value=True, key="text_collapse_opt")

        params = {"columns": target_cols or None, "case": case_opt, "strip": strip_opt, "collapse_spaces": collapse_opt}
        prev = preview_operation(df, "standardize_text", params)
        st.caption(f"Estimated rows affected: **{prev['rows_affected']:,}**")

        if st.button("Apply Text Formatting", key="btn_apply_text"):
            _apply_step(bundle, "standardize_text", params, "text", "safe", target_cols or str_cols)

    with c2:
        st.markdown("**Harmonize Variants**")
        st.caption("Replace irregular category labels (e.g. 'USA', 'U.S.', 'United States' ➜ 'United States').")
        harm_col = st.selectbox("Select column to harmonize:", str_cols, key="text_harm_col")
        if harm_col:
            val_counts = df[harm_col].value_counts().head(10).to_dict()
            st.caption(f"Top values in `{harm_col}`: {', '.join(list(val_counts.keys())[:5])}")
            find_str = st.text_input("Find exact value:", key="text_find_val")
            replace_str = st.text_input("Replace with:", key="text_replace_val")
            if st.button("Replace Variant", disabled=not find_str, key="btn_replace_variant"):
                _apply_step(bundle, "harmonize_variants", {"column": harm_col, "mapping": {find_str: replace_str}}, "text", "review", [harm_col])


def _render_stage_invalid(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 4: Invalid values and placeholders."""
    st.markdown("#### 4. Invalid Values & Sentinel Placeholders")
    st.caption("Detect and replace placeholders like 'N/A', '-', '999', 'null' with genuine missing values (NaN).")

    default_ph = "N/A, n/a, NA, na, -, --, none, None, null, Null, 999, -999, ?"
    custom_ph = st.text_area("Sentinel placeholder strings (comma-separated):", value=default_ph, key="inv_placeholders_str")
    placeholders_list = [p.strip() for p in custom_ph.split(",") if p.strip()]

    prev = preview_operation(df, "replace_placeholders", {"placeholders": placeholders_list})
    st.info(f"Detected **{prev['rows_affected']:,}** cells containing sentinel placeholders across the dataset.")

    if st.button("Convert Placeholders to NaN", key="btn_clean_placeholders"):
        _apply_step(bundle, "replace_placeholders", {"placeholders": placeholders_list}, "invalid_values", "safe", list(df.columns))


def _render_stage_duplicates(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 5: Duplicates."""
    st.markdown("#### 5. Duplicate Rows")
    st.caption("Identify and drop duplicate records.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Exact Duplicates**")
        exact_dups = int(df.duplicated().sum())
        st.write(f"Fully identical rows: **{exact_dups:,}** ({exact_dups / max(1, len(df)) * 100:.1f}%)")
        if st.button("Remove Exact Duplicates", disabled=exact_dups == 0, key="btn_remove_exact_dups"):
            _apply_step(bundle, "remove_duplicates", {}, "duplicates", "safe", list(df.columns))

    with c2:
        st.markdown("**Subset Duplicates (Review)**")
        st.caption("Check uniqueness on specific ID / business key columns.")
        key_cols = st.multiselect("Key columns:", list(df.columns), key="dups_key_cols")
        if key_cols:
            subset_dups = int(df.duplicated(subset=key_cols).sum())
            st.write(f"Duplicates based on keys: **{subset_dups:,}**")
            keep_opt = st.selectbox("Keep occurrence:", ["first", "last"], key="dups_keep_opt")
            if st.button("Remove Subset Duplicates", disabled=subset_dups == 0, key="btn_remove_subset_dups"):
                _apply_step(bundle, "remove_duplicates", {"subset": key_cols, "keep": keep_opt}, "duplicates", "review", key_cols)


def _render_stage_missing(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 6: Missing values."""
    st.markdown("#### 6. Missing Values Imputation & Pruning")
    st.caption("Impute numeric and categorical missing values with domain-appropriate strategies.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Per-Column Imputation**")
        missing_cols = [c for c in df.columns if df[c].isna().sum() > 0]
        if not missing_cols:
            st.success("No missing values found in any column!")
        else:
            col_to_fill = st.selectbox("Select column to impute:", missing_cols, key="miss_col_sel")
            col_missing_cnt = int(df[col_to_fill].isna().sum())
            st.caption(f"`{col_to_fill}` has **{col_missing_cnt:,}** missing values ({col_missing_cnt / len(df) * 100:.1f}%).")

            is_numeric = pd.api.types.is_numeric_dtype(df[col_to_fill])
            strategies = ["median", "mean", "mode", "constant", "ffill", "drop_rows"] if is_numeric else ["mode", "constant", "drop_rows"]
            strat = st.selectbox("Imputation strategy:", strategies, key="miss_strat_sel")

            const_val = None
            if strat == "constant":
                const_val = st.text_input("Constant fill value:", value="0" if is_numeric else "Unknown", key="miss_const_val")
                if is_numeric:
                    try:
                        const_val = float(const_val)
                    except ValueError:
                        const_val = 0.0

            if st.button("Apply Imputation", key="btn_apply_impute"):
                op_name = "fill_missing_numeric" if is_numeric else "fill_missing_categorical"
                params = {"column": col_to_fill, "method": strat, "constant_value": const_val, "columns": [col_to_fill]}
                _apply_step(bundle, op_name, params, "missing_values", "review", [col_to_fill])

    with c2:
        st.markdown("**Drop Heavy-Missing Columns (Risky)**")
        st.caption("Drop columns where missing value percentage exceeds a threshold.")
        thresh = st.slider("Missingness threshold (%):", min_value=10, max_value=90, value=50, step=5, key="miss_drop_col_thresh")
        candidate_cols = [c for c in df.columns if df[c].isna().mean() > (thresh / 100.0)]
        st.write(f"Columns exceeding {thresh}% missingness: **{len(candidate_cols)}** ({', '.join(candidate_cols) if candidate_cols else 'None'})")

        approve_col_drop = st.checkbox("I approve dropping these columns (Risky)", key="miss_approve_col_drop")
        if st.button("Drop High-Missing Columns", disabled=not approve_col_drop or len(candidate_cols) == 0, key="btn_drop_miss_cols"):
            _apply_step(bundle, "drop_missing_columns", {"threshold_pct": float(thresh)}, "missing_values", "risky", candidate_cols)


def _render_stage_outliers(df: pd.DataFrame, bundle: DatasetBundle) -> None:
    """Stage 7: Outliers (flag by default, cap/remove only on approval)."""
    st.markdown("#### 7. Outliers (Flag, Cap, or Remove)")
    st.caption("Outliers are flagged by default. Capping (Winsorizing) or removal modifies data and strictly requires approval.")

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        st.info("No numeric columns available for outlier detection.")
        return

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**1. Outlier Inspection (Read-Only Flagging)**")
        factor = st.slider("IQR Multiplier (typically 1.5):", min_value=1.0, max_value=3.0, value=1.5, step=0.1, key="outlier_factor")
        outlier_counts = {}
        for c in num_cols:
            valid = df[c].dropna()
            if len(valid) >= 4:
                q25 = valid.quantile(0.25)
                q75 = valid.quantile(0.75)
                iqr = q75 - q25
                cnt = int(((df[c] < (q25 - factor * iqr)) | (df[c] > (q75 + factor * iqr))).sum())
                if cnt > 0:
                    outlier_counts[c] = cnt

        if outlier_counts:
            st.write("Columns with detected outliers:")
            for col_name, cnt in outlier_counts.items():
                st.write(f"- `{col_name}`: **{cnt:,}** outlier values ({cnt / len(df) * 100:.1f}%)")
        else:
            st.success("No outliers detected based on the current IQR factor.")

    with col2:
        st.markdown("**2. Outlier Treatment (Risky - Requires Approval)**")
        target_outlier_cols = st.multiselect("Select columns to treat:", list(outlier_counts.keys()), key="outlier_treat_cols")
        treatment_method = st.radio("Treatment Action:", ["Cap values (Winsorize to fences)", "Remove outlier rows"], key="outlier_action_radio")

        st.warning("⚠️ Capping or removing outliers alters distributions and requires explicit user consent.")
        approve_outliers = st.checkbox("I approve this outlier treatment (Risky)", key="outlier_approval_checkbox")

        if st.button("Apply Outlier Treatment", disabled=not approve_outliers or not target_outlier_cols, key="btn_apply_outliers"):
            op = "cap_outliers" if "Cap" in treatment_method else "remove_outliers"
            params = {"columns": target_outlier_cols, "factor": float(factor)}
            _apply_step(bundle, op, params, "outliers", "risky", target_outlier_cols)


def _render_stage_validation(df: pd.DataFrame) -> None:
    """Stage 8: Final validation."""
    st.markdown("#### 8. Final Validation")
    st.caption("Integrity and completeness checklist for the current working dataset.")

    v = clean_validate_dataset(df)

    v1, v2, v3, v4 = st.columns(4)
    with v1:
        st.metric("Total Rows", f"{v['rows']:,}")
    with v2:
        st.metric("Total Columns", f"{v['cols']}")
    with v3:
        st.metric("Missing %", f"{v['missing_pct']:.2f}%")
    with v4:
        st.metric("Duplicates", f"{v['duplicate_rows']:,}")

    if v["valid"]:
        st.success("✅ Dataset structure is intact, non-empty, and ready for analytics or export.")
    else:
        st.error("❌ Dataset failed validation: check whether rows or columns were completely pruned.")


def page() -> None:
    """Render the main Data Cleaning page."""
    st.markdown('<div class="animate-fade-in">', unsafe_allow_html=True)
    st.title("🧹 Data Cleaning Pipeline")
    st.caption("Ordered 8-stage data cleaning workspace. In-memory versioning ensures zero risk to original data.")
    st.markdown("---")

    if not has_dataset():
        st.markdown(
            """
            <div class="empty-state">
                <div class="empty-state-icon">🧹</div>
                <div class="empty-state-title">No Dataset Loaded</div>
                <div class="empty-state-desc">
                    Upload a dataset to access the cleaning pipeline.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    bundle = get_bundle()
    if bundle is None:
        st.info("No dataset is available for cleaning.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Top Toolbar (Auto-clean, Undo, Reset)
    _render_top_toolbar(bundle)
    st.markdown("---")

    # 8-Stage Tabs
    tabs = st.tabs([
        "1. 🏗️ Structure",
        "2. 🔤 Types",
        "3. 📝 Text",
        "4. ⚠️ Placeholders",
        "5. 👥 Duplicates",
        "6. ❓ Missing Values",
        "7. 🎯 Outliers",
        "8. ✅ Validation",
    ])

    with tabs[0]:
        _render_stage_structure(bundle.working_df, bundle)
    with tabs[1]:
        _render_stage_types(bundle.working_df, bundle)
    with tabs[2]:
        _render_stage_text(bundle.working_df, bundle)
    with tabs[3]:
        _render_stage_invalid(bundle.working_df, bundle)
    with tabs[4]:
        _render_stage_duplicates(bundle.working_df, bundle)
    with tabs[5]:
        _render_stage_missing(bundle.working_df, bundle)
    with tabs[6]:
        _render_stage_outliers(bundle.working_df, bundle)
    with tabs[7]:
        _render_stage_validation(bundle.working_df)

    st.markdown("---")

    # Working Dataset Sample View
    with st.expander("🔍 View Current Working Dataset Preview (First 50 Rows)", expanded=False):
        st.dataframe(bundle.working_df.head(50), width="stretch")

    # Audit Log Table
    history = getattr(bundle, "transformation_history", [])
    if history:
        with st.expander(f"📜 Audit Log ({len(history)} operations applied)", expanded=False):
            log_records = []
            for idx, item in enumerate(history, start=1):
                log_records.append({
                    "Step": idx,
                    "Timestamp": getattr(item, "timestamp", ""),
                    "Stage": getattr(item, "stage", "cleaning"),
                    "Risk": getattr(item, "risk", "safe").upper(),
                    "Operation": getattr(item, "operation", ""),
                    "Rows Affected": getattr(item, "rows_affected", 0),
                    "Parameters": json.dumps(getattr(item, "params", {})),
                })
            st.dataframe(pd.DataFrame(log_records), width="stretch", hide_index=True)

    # Recipe Save & Load
    with st.expander("📖 Cleaning Recipes (Save / Load JSON)", expanded=False):
        from core.recipes import apply_recipe, load_recipe, save_recipe, validate_recipe_compatibility
        rcol1, rcol2 = st.columns(2)

        with rcol1:
            st.markdown("**💾 Save Current Cleaning Recipe**")
            st.caption("Export applied cleaning operations as a reusable JSON recipe for future datasets.")
            recipe_name = st.text_input("Recipe Name:", value="dataset_cleaning_recipe", key="clean_recipe_name_input")
            recipe_desc = st.text_area("Description:", value="Reusable cleaning pipeline steps.", key="clean_recipe_desc_input")
            recipe_json = save_recipe(history, name=recipe_name, description=recipe_desc)
            st.download_button(
                label="⬇️ Download Recipe JSON",
                data=recipe_json.encode("utf-8"),
                file_name=f"{recipe_name}.json",
                mime="application/json",
                key="clean_download_recipe_btn",
            )

        with rcol2:
            st.markdown("**📂 Load & Apply Saved Recipe**")
            st.caption("Upload a previously saved .json recipe to apply its steps to this dataset.")
            uploaded_recipe = st.file_uploader("Upload Recipe JSON", type=["json"], key="clean_recipe_uploader")
            if uploaded_recipe is not None:
                try:
                    loaded_recipe_str = uploaded_recipe.getvalue().decode("utf-8")
                    recipe_obj = load_recipe(loaded_recipe_str)
                    st.write(f"Loaded: **{recipe_obj.name}** ({len(recipe_obj.steps)} steps)")
                    compat, comp_warns = validate_recipe_compatibility(recipe_obj, bundle.working_df)
                    if not compat:
                        st.error(f"Incompatible recipe: {comp_warns[0]}")
                    else:
                        if comp_warns:
                            for w in comp_warns:
                                st.warning(w)
                        if st.button("▶️ Apply Recipe to Current Data", key="clean_apply_recipe_btn"):
                            bundle.push_snapshot()
                            rec_cleaned_df, rec_records, rec_warns = apply_recipe(bundle.working_df, recipe_obj)
                            bundle.working_df = rec_cleaned_df
                            bundle.transformation_history.extend(rec_records)
                            set_bundle(bundle)
                            st.success(f"Recipe applied successfully! {len(rec_records)} operations executed.")
                            st.rerun()
                except Exception as e:
                    st.error(f"Failed to parse recipe file: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
