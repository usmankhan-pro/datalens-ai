"""EDA (Exploratory Data Analysis) analytical engine for DataLens AI.

Runs strictly on real DataFrame computations:
- Overview (structure, memory, column types)
- Univariate (distributions, cardinality, skewness, percentiles)
- Missing-value patterns & co-occurrence
- Outlier detection (IQR fences, z-scores)
- Bivariate analysis (Pearson & Spearman correlations, group comparisons with min 5 per group)
- Target column analysis (classification balance or regression correlation)
- Time trends (temporal aggregation if datetime columns exist)
- Top 5 plain-language insights generated from real numbers
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def compute_eda_overview(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute high-level structural and type summary of the dataset."""
    if df is None or df.empty:
        return {
            "rows": 0, "cols": 0, "memory_mb": 0.0, "duplicate_rows": 0,
            "duplicate_pct": 0.0, "missing_cells": 0, "missing_pct": 0.0,
            "col_types": {"numeric": 0, "categorical": 0, "datetime": 0, "boolean": 0},
            "columns": [],
        }

    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    missing_cells = int(df.isna().sum().sum())
    missing_pct = (missing_cells / total_cells * 100.0) if total_cells > 0 else 0.0
    duplicate_rows = int(df.duplicated().sum())
    duplicate_pct = (duplicate_rows / total_rows * 100.0) if total_rows > 0 else 0.0
    memory_mb = float(df.memory_usage(deep=True).sum() / (1024 * 1024))
    # Keep 3 decimal places so even small frames (< 1 MB) show exact memory
    memory_mb_display = round(memory_mb, 3) if memory_mb >= 0.001 else 0.001

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    bool_cols = [c for c in df.columns if pd.api.types.is_bool_dtype(df[c])]
    cat_cols = [c for c in df.columns if c not in num_cols and c not in date_cols and c not in bool_cols]

    return {
        "rows": total_rows,
        "cols": total_cols,
        "memory_mb": memory_mb_display,
        "duplicate_rows": duplicate_rows,
        "duplicate_pct": round(duplicate_pct, 2),
        "missing_cells": missing_cells,
        "missing_pct": round(missing_pct, 2),
        "col_types": {
            "numeric": len(num_cols),
            "categorical": len(cat_cols),
            "datetime": len(date_cols),
            "boolean": len(bool_cols),
        },
        "columns": list(df.columns),
        "numeric_cols": num_cols,
        "categorical_cols": cat_cols,
        "datetime_cols": date_cols,
        "boolean_cols": bool_cols,
    }


def compute_univariate_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute univariate statistics for all numeric and categorical columns."""
    if df is None or df.empty:
        return {"numeric": {}, "categorical": {}}

    numeric_results: Dict[str, Any] = {}
    categorical_results: Dict[str, Any] = {}

    for col in df.columns:
        series = df[col]
        total_len = len(series)
        missing_cnt = int(series.isna().sum())
        non_null_cnt = total_len - missing_cnt
        unique_cnt = int(series.nunique(dropna=True))

        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            valid = series.dropna()
            if len(valid) == 0:
                continue

            mean_val = float(valid.mean())
            std_val = float(valid.std()) if len(valid) > 1 else 0.0
            min_val = float(valid.min())
            q25 = float(valid.quantile(0.25))
            median_val = float(valid.median())
            q75 = float(valid.quantile(0.75))
            max_val = float(valid.max())
            iqr_val = q75 - q25

            skew_val = float(valid.skew()) if len(valid) > 2 else 0.0
            kurt_val = float(valid.kurtosis()) if len(valid) > 3 else 0.0

            # Histogram bins (10 equal-width bins)
            hist_counts, bin_edges = np.histogram(valid, bins=min(10, max(2, unique_cnt)))

            numeric_results[col] = {
                "count": non_null_cnt,
                "missing": missing_cnt,
                "missing_pct": round(missing_cnt / total_len * 100.0, 2),
                "unique": unique_cnt,
                "mean": round(mean_val, 3),
                "std": round(std_val, 3),
                "min": round(min_val, 3),
                "q25": round(q25, 3),
                "median": round(median_val, 3),
                "q75": round(q75, 3),
                "max": round(max_val, 3),
                "iqr": round(iqr_val, 3),
                "skewness": round(skew_val, 3),
                "kurtosis": round(kurt_val, 3),
                "hist_counts": hist_counts.tolist(),
                "bin_edges": [round(float(b), 2) for b in bin_edges],
            }
        else:
            # Categorical or boolean
            valid = series.dropna().astype(str)
            top_counts = valid.value_counts().head(10).to_dict()
            mode_val = valid.mode().iloc[0] if not valid.empty else "N/A"
            top_freq = int(valid.value_counts().iloc[0]) if not valid.empty else 0
            top_pct = round(top_freq / max(1, non_null_cnt) * 100.0, 2)

            categorical_results[col] = {
                "count": non_null_cnt,
                "missing": missing_cnt,
                "missing_pct": round(missing_cnt / total_len * 100.0, 2),
                "unique": unique_cnt,
                "mode": mode_val,
                "top_freq": top_freq,
                "top_pct": top_pct,
                "top_values": top_counts,
            }

    return {"numeric": numeric_results, "categorical": categorical_results}


def compute_missing_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute per-column missing statistics and co-occurrence patterns."""
    if df is None or df.empty:
        return {"column_missing": {}, "co_occurrence": [], "row_missing_distribution": {}}

    total_rows = len(df)
    col_missing: Dict[str, Dict[str, Any]] = {}

    for c in df.columns:
        cnt = int(df[c].isna().sum())
        col_missing[c] = {
            "count": cnt,
            "pct": round(cnt / total_rows * 100.0, 2),
        }

    # Sort columns by missing percentage descending
    sorted_missing = dict(sorted(col_missing.items(), key=lambda x: x[1]["count"], reverse=True))

    # Co-occurrence between columns with missing values
    miss_cols = [c for c, d in col_missing.items() if d["count"] > 0]
    co_occurrence = []
    if len(miss_cols) >= 2:
        for i in range(len(miss_cols)):
            for j in range(i + 1, min(len(miss_cols), i + 6)):
                c1, c2 = miss_cols[i], miss_cols[j]
                both_missing = int((df[c1].isna() & df[c2].isna()).sum())
                if both_missing > 0:
                    co_occurrence.append({
                        "col1": c1,
                        "col2": c2,
                        "co_missing_rows": both_missing,
                        "co_missing_pct": round(both_missing / total_rows * 100.0, 2),
                    })

    # Distribution of missingness per row
    rows_missing_cnt = df.isna().sum(axis=1)
    row_dist = {
        "0 missing": int((rows_missing_cnt == 0).sum()),
        "1 missing": int((rows_missing_cnt == 1).sum()),
        "2-3 missing": int(((rows_missing_cnt >= 2) & (rows_missing_cnt <= 3)).sum()),
        ">3 missing": int((rows_missing_cnt > 3).sum()),
    }

    return {
        "column_missing": sorted_missing,
        "co_occurrence": sorted(co_occurrence, key=lambda x: x["co_missing_rows"], reverse=True),
        "row_missing_distribution": row_dist,
    }


def compute_outlier_analysis(df: pd.DataFrame, factor: float = 1.5) -> Dict[str, Any]:
    """Compute IQR fences and Z-score outlier metrics for numeric columns."""
    if df is None or df.empty:
        return {}

    outliers: Dict[str, Any] = {}
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]

    for col in num_cols:
        valid = df[col].dropna()
        if len(valid) < 4:
            continue

        q25 = float(valid.quantile(0.25))
        q75 = float(valid.quantile(0.75))
        iqr = q75 - q25
        lower_fence = q25 - factor * iqr
        upper_fence = q75 + factor * iqr

        iqr_mask = (valid < lower_fence) | (valid > upper_fence)
        iqr_count = int(iqr_mask.sum())
        iqr_pct = round(iqr_count / len(valid) * 100.0, 2)

        # Z-Score method (|z| > 3.0)
        mean_val = float(valid.mean())
        std_val = float(valid.std()) if len(valid) > 1 else 0.0
        z_count = 0
        z_pct = 0.0
        if std_val > 0:
            z_scores = np.abs((valid - mean_val) / std_val)
            z_count = int((z_scores > 3.0).sum())
            z_pct = round(z_count / len(valid) * 100.0, 2)

        outlier_vals = valid[iqr_mask]
        min_outlier = float(outlier_vals.min()) if not outlier_vals.empty else None
        max_outlier = float(outlier_vals.max()) if not outlier_vals.empty else None

        outliers[col] = {
            "lower_fence": round(lower_fence, 2),
            "upper_fence": round(upper_fence, 2),
            "iqr_count": iqr_count,
            "iqr_pct": iqr_pct,
            "z_count": z_count,
            "z_pct": z_pct,
            "min_outlier": min_outlier,
            "max_outlier": max_outlier,
            "median": round(float(valid.median()), 2),
        }

    return outliers


def compute_bivariate_analysis(df: pd.DataFrame, min_group_size: int = 5) -> Dict[str, Any]:
    """
    Compute Pearson & Spearman correlation matrices and group comparisons with min 5 per group.
    """
    if df is None or df.empty:
        return {"pearson": {}, "spearman": {}, "group_comparisons": []}

    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
    cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c])]

    pearson_matrix: Dict[str, Dict[str, float]] = {}
    spearman_matrix: Dict[str, Dict[str, float]] = {}

    if len(num_cols) >= 2:
        num_df = df[num_cols].dropna()
        if len(num_df) >= 3:
            p_corr = num_df.corr(method="pearson").round(3)
            s_corr = num_df.corr(method="spearman").round(3)

            for c in num_cols:
                pearson_matrix[c] = {other: float(p_corr.loc[c, other]) for other in num_cols if not pd.isna(p_corr.loc[c, other])}
                spearman_matrix[c] = {other: float(s_corr.loc[c, other]) for other in num_cols if not pd.isna(s_corr.loc[c, other])}

    # Group comparisons: numeric metric split by categorical groups with min_group_size >= 5
    group_comparisons: List[Dict[str, Any]] = []
    for c_col in cat_cols[:4]:  # limit to top 4 categoricals
        if df[c_col].nunique() < 2 or df[c_col].nunique() > 15:
            continue
        for n_col in num_cols[:4]:  # limit to top 4 numerics
            valid_subset = df[[c_col, n_col]].dropna()
            # Filter groups with min_group_size
            grp_counts = valid_subset[c_col].value_counts()
            qualifying_groups = grp_counts[grp_counts >= min_group_size].index.tolist()

            if len(qualifying_groups) >= 2:
                filtered_df = valid_subset[valid_subset[c_col].isin(qualifying_groups)]
                grouped_stats = (
                    filtered_df.groupby(c_col)[n_col]
                    .agg(count="count", mean="mean", median="median", std="std")
                    .round(2)
                    .reset_index()
                )
                stats_list = grouped_stats.to_dict(orient="records")

                # ANOVA F-test
                group_arrays = [filtered_df[filtered_df[c_col] == g][n_col].values for g in qualifying_groups]
                try:
                    f_stat, p_val = stats.f_oneway(*group_arrays)
                    f_stat_clean = round(float(f_stat), 3) if not np.isnan(f_stat) else 0.0
                    p_val_clean = round(float(p_val), 4) if not np.isnan(p_val) else 1.0
                except Exception:
                    f_stat_clean, p_val_clean = 0.0, 1.0

                group_comparisons.append({
                    "categorical_col": c_col,
                    "numeric_col": n_col,
                    "groups_compared": len(qualifying_groups),
                    "f_statistic": f_stat_clean,
                    "p_value": p_val_clean,
                    "is_statistically_significant": p_val_clean < 0.05,
                    "group_stats": stats_list,
                })

    return {
        "pearson": pearson_matrix,
        "spearman": spearman_matrix,
        "group_comparisons": group_comparisons,
    }


def compute_target_analysis(df: pd.DataFrame, target_col: str, min_group_size: int = 5) -> Dict[str, Any]:
    """Compute detailed target variable analytics (classification or regression)."""
    if df is None or df.empty or target_col not in df.columns:
        return {}

    target = df[target_col]
    total_rows = len(target)
    missing_cnt = int(target.isna().sum())
    valid = target.dropna()

    is_numeric = pd.api.types.is_numeric_dtype(target) and not pd.api.types.is_bool_dtype(target)

    if is_numeric and target.nunique() > 10:
        # Continuous regression target
        correlations: List[Dict[str, Any]] = []
        num_cols = [c for c in df.columns if c != target_col and pd.api.types.is_numeric_dtype(df[c])]
        for col in num_cols:
            subset = df[[col, target_col]].dropna()
            if len(subset) >= 5 and subset[col].nunique() > 1 and subset[target_col].nunique() > 1:
                r_val, _ = stats.pearsonr(subset[col], subset[target_col])
                rho_val, _ = stats.spearmanr(subset[col], subset[target_col])
                if not np.isnan(r_val):
                    correlations.append({
                        "feature": col,
                        "pearson_r": round(float(r_val), 3),
                        "spearman_rho": round(float(rho_val), 3),
                        "abs_pearson": abs(float(r_val)),
                    })

        sorted_corr = sorted(correlations, key=lambda x: x["abs_pearson"], reverse=True)

        return {
            "target_type": "continuous (regression)",
            "target_name": target_col,
            "count": len(valid),
            "missing": missing_cnt,
            "mean": round(float(valid.mean()), 3),
            "median": round(float(valid.median()), 3),
            "std": round(float(valid.std()), 3),
            "min": round(float(valid.min()), 3),
            "max": round(float(valid.max()), 3),
            "correlations": sorted_corr,
        }
    else:
        # Categorical / Discrete classification target
        counts = valid.value_counts()
        total_valid = len(valid)
        class_balance: Dict[str, Dict[str, Any]] = {}
        for cls_name, cnt in counts.items():
            class_balance[str(cls_name)] = {
                "count": int(cnt),
                "pct": round(cnt / max(1, total_valid) * 100.0, 2),
            }

        imbalance_ratio = 1.0
        if len(counts) >= 2:
            imbalance_ratio = round(float(counts.iloc[0] / max(1, counts.iloc[-1])), 2)

        return {
            "target_type": "categorical (classification)",
            "target_name": target_col,
            "classes": len(counts),
            "count": total_valid,
            "missing": missing_cnt,
            "imbalance_ratio": imbalance_ratio,
            "is_imbalanced": imbalance_ratio > 3.0,
            "class_balance": class_balance,
        }


def compute_time_trends(df: pd.DataFrame, date_col: Optional[str] = None) -> Dict[str, Any]:
    """Aggregate numeric metrics over datetime columns."""
    if df is None or df.empty:
        return {}

    date_columns = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    if not date_columns:
        return {}

    target_date = date_col if date_col in date_columns else date_columns[0]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]

    valid_df = df.dropna(subset=[target_date]).copy()
    if valid_df.empty:
        return {}

    min_date = str(valid_df[target_date].min())
    max_date = str(valid_df[target_date].max())
    span_days = int((valid_df[target_date].max() - valid_df[target_date].min()).days)

    # Monthly aggregation
    valid_df["_period"] = valid_df[target_date].dt.to_period("M").astype(str)
    period_counts = valid_df["_period"].value_counts().sort_index().to_dict()

    numeric_trends: Dict[str, Dict[str, float]] = {}
    if num_cols:
        primary_num = num_cols[0]
        agg_means = valid_df.groupby("_period")[primary_num].mean().round(2).to_dict()
        numeric_trends[primary_num] = agg_means

    return {
        "date_column": target_date,
        "min_date": min_date,
        "max_date": max_date,
        "span_days": span_days,
        "period_counts": period_counts,
        "numeric_trends": numeric_trends,
    }


def compute_top_insights(df: pd.DataFrame, target_col: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generate top 5 plain-language insights computed strictly from real DataFrame numbers.
    """
    insights: List[Dict[str, Any]] = []
    if df is None or df.empty:
        return insights

    total_rows = len(df)
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])]
    cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c])]

    # 1. Strongest Correlation Insight
    if len(num_cols) >= 2:
        valid_num = df[num_cols].dropna()
        if len(valid_num) >= 5:
            corr_matrix = valid_num.corr(method="pearson")
            best_pair = None
            max_abs_r = -1.0
            for i in range(len(num_cols)):
                for j in range(i + 1, len(num_cols)):
                    c1, c2 = num_cols[i], num_cols[j]
                    val = corr_matrix.loc[c1, c2]
                    if not np.isnan(val) and abs(val) > max_abs_r:
                        max_abs_r = abs(val)
                        best_pair = (c1, c2, float(val))

            if best_pair and max_abs_r >= 0.2:
                c1, c2, r_val = best_pair
                direction = "positive" if r_val > 0 else "negative"
                strength = "strong" if max_abs_r >= 0.7 else ("moderate" if max_abs_r >= 0.4 else "slight")
                insights.append({
                    "category": "Correlation",
                    "text": (
                        f"Features '{c1}' and '{c2}' exhibit a {strength} {direction} correlation of r = {r_val:.2f}."
                    ),
                    "significance": "high" if max_abs_r >= 0.7 else "medium",
                })

    # 2. Missing Value Concentration Insight
    missing_series = df.isna().sum()
    worst_col = missing_series.idxmax()
    worst_cnt = int(missing_series.max())
    if worst_cnt > 0:
        worst_pct = round(worst_cnt / total_rows * 100.0, 1)
        insights.append({
            "category": "Missing Data",
            "text": (
                f"Missing values are concentrated in '{worst_col}', with {worst_cnt:,} null entries ({worst_pct}% of total rows)."
            ),
            "significance": "high" if worst_pct > 20 else "medium",
        })
    else:
        insights.append({
            "category": "Data Completeness",
            "text": f"The dataset is 100% complete with 0 missing values across all {len(df.columns)} columns.",
            "significance": "low",
        })

    # 3. Categorical Dominance / Cardinality Insight
    if cat_cols:
        for c in cat_cols:
            val_counts = df[c].dropna().value_counts()
            if not val_counts.empty and len(val_counts) > 1:
                top_name = str(val_counts.index[0])
                top_cnt = int(val_counts.iloc[0])
                top_pct = round(top_cnt / max(1, df[c].notna().sum()) * 100.0, 1)
                if top_pct >= 60.0:
                    insights.append({
                        "category": "Category Imbalance",
                        "text": (
                            f"Column '{c}' is heavily dominated by category '{top_name}', accounting for {top_pct}% ({top_cnt:,} of {df[c].notna().sum():,} non-null rows)."
                        ),
                        "significance": "medium",
                    })
                    break

    # 4. Outlier Impact Insight
    outlier_dict = compute_outlier_analysis(df, factor=1.5)
    worst_outlier_col = None
    max_outlier_pct = 0.0
    for col, data in outlier_dict.items():
        if data["iqr_pct"] > max_outlier_pct and data["iqr_count"] > 0:
            max_outlier_pct = data["iqr_pct"]
            worst_outlier_col = col

    if worst_outlier_col and max_outlier_pct >= 2.0:
        o_data = outlier_dict[worst_outlier_col]
        insights.append({
            "category": "Outlier Detection",
            "text": (
                f"Column '{worst_outlier_col}' has {o_data['iqr_count']:,} values ({max_outlier_pct}%) outside standard IQR fences "
                f"(median: {o_data['median']}, max extreme: {o_data['max_outlier']})."
            ),
            "significance": "medium" if max_outlier_pct < 10 else "high",
        })

    # 5. Target Analysis or Group Differences Insight
    if target_col and target_col in df.columns:
        target_info = compute_target_analysis(df, target_col)
        if target_info.get("target_type") == "categorical (classification)":
            ratio = target_info.get("imbalance_ratio", 1.0)
            insights.append({
                "category": "Target Analysis",
                "text": (
                    f"Target column '{target_col}' has {target_info['classes']} distinct classes with an imbalance ratio of {ratio}:1."
                ),
                "significance": "high" if ratio > 3.0 else "low",
            })
        elif target_info.get("target_type") == "continuous (regression)":
            top_corr = target_info.get("correlations", [])
            if top_corr:
                t_lead = top_corr[0]
                insights.append({
                    "category": "Target Predictor",
                    "text": (
                        f"Feature '{t_lead['feature']}' is the strongest predictor of target '{target_col}' (Pearson r = {t_lead['pearson_r']:.2f})."
                    ),
                    "significance": "high",
                })

    # Fallback to group comparison if fewer than 5 insights
    if len(insights) < 5:
        bivariate = compute_bivariate_analysis(df, min_group_size=5)
        grp_comps = bivariate.get("group_comparisons", [])
        for comp in grp_comps:
            if comp["is_statistically_significant"]:
                insights.append({
                    "category": "Group Variance",
                    "text": (
                        f"Statistically significant variation found in '{comp['numeric_col']}' across categories of '{comp['categorical_col']}' "
                        f"(F-statistic = {comp['f_statistic']:.2f}, p-value = {comp['p_value']:.4f})."
                    ),
                    "significance": "medium",
                })
                break

    # If still fewer than 5, add duplicate row insight or data volume insight
    if len(insights) < 5:
        dups = int(df.duplicated().sum())
        if dups > 0:
            dup_pct = round(dups / total_rows * 100.0, 1)
            insights.append({
                "category": "Data Uniqueness",
                "text": f"Found {dups:,} duplicate rows ({dup_pct}%), which may distort model training or KPI aggregations.",
                "significance": "medium",
            })
        else:
            insights.append({
                "category": "Data Volume",
                "text": f"Dataset consists of {total_rows:,} verified unique rows across {len(df.columns)} dimensions.",
                "significance": "low",
            })

    return insights[:5]


def run_full_eda(df: pd.DataFrame, target_col: Optional[str] = None) -> Dict[str, Any]:
    """Execute complete EDA pipeline on a DataFrame."""
    return {
        "overview": compute_eda_overview(df),
        "univariate": compute_univariate_analysis(df),
        "missing_patterns": compute_missing_patterns(df),
        "outliers": compute_outlier_analysis(df),
        "bivariate": compute_bivariate_analysis(df, min_group_size=5),
        "target": compute_target_analysis(df, target_col) if target_col else {},
        "time_trends": compute_time_trends(df),
        "top_insights": compute_top_insights(df, target_col=target_col),
    }
