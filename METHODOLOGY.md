# Methodology

This document defines the mathematical models, statistical thresholds, and rule-based logic governing DataLens AI.

---

## 1. Data Quality Score

The overall data quality score is a normalized composite index computed as:

$$
\text{Overall Quality Score} = 0.30 \times \text{Completeness} + 0.15 \times \text{Uniqueness} + 0.25 \times \text{Validity} + 0.20 \times \text{Consistency} + 0.10 \times \text{AccuracyIndicator}
$$

### Dimensions
* **Completeness**: $100 \times \left(1 - \frac{\text{missing\_cells}}{\text{total\_cells}}\right)$
* **Uniqueness**: $100 \times \left(1 - \frac{\text{duplicate\_rows}}{\text{total\_rows}}\right)$, with an additional penalty if duplicated primary identifier keys are detected.
* **Validity**: $100 \times \left(1 - \frac{\text{invalid\_cells}}{\text{checked\_cells}}\right)$ (evaluates sentinel placeholders, impossible negative values, format errors).
* **Consistency**: Evaluates mixed data types in single columns, irregular date syntax, and constant/zero-variance features.
* **Accuracy Indicator**: Outlier-adjusted score derived from IQR and Z-score distributions.

---

## 2. 8-Stage Cleaning Pipeline Architecture

Cleaning transformations execute in a strict, deterministic sequence designed to maximize data integrity without circular dependencies:

1. **Structure**: Drops completely empty rows/columns and normalizes column headers to snake_case. *(Safety: Safe)*
2. **Types**: Converts formatted strings (currency symbols `$`, percentages `%`, accounting negatives `(x)`) to numeric floats, parses ISO/custom datetimes, and standardizes boolean tokens. *(Safety: Safe)*
3. **Text**: Trims trailing/leading whitespace, collapses redundant internal spaces, and normalizes casing. *(Safety: Safe)*
4. **Invalid Values & Placeholders**: Replaces sentinel text (`'N/A'`, `'-'`, `'999'`, `'null'`, `'?'`) with genuine `np.nan` nulls so they are treated accurately by downstream engines. *(Safety: Safe)*
5. **Duplicates**: Drops exact full-row duplicate records. *(Safety: Safe)*
6. **Missing Values**: Per-column imputation (numeric median/mean, categorical mode or constant `"Unknown"`). Heavy-missing column dropping (>50%) is marked as *(Safety: Risky)*.
7. **Outliers**: Outliers are flagged by default using IQR fences ($Q_1 - 1.5 \cdot \text{IQR}$, $Q_3 + 1.5 \cdot \text{IQR}$). Capping (Winsorizing) or record removal modifies underlying distributions and strictly requires user approval *(Safety: Risky)*.
8. **Final Validation**: Evaluates shape integrity, confirms non-empty status, and verifies type stability. *(Safety: Safe)*

---

## 3. Goal-Aware Action Planning Rules

The Action Planner dynamically adjusts cleaning priorities based on the declared `UserContext`:

| Analytical Goal | High-Priority Focus Areas | Rationale |
| :--- | :--- | :--- |
| **Machine Learning (`ml`)** | Class imbalance, leaky ID features, high cardinality categoricals, numeric median imputation | Supervised algorithms fail on missing values, overfit on unique IDs, and suffer severe performance degradation from target leakage and class skew. |
| **Reporting (`reporting`)** | Duplicate rows, datetime parsing, missing KPI fields, header snake_casing | Duplicates double-count aggregated totals (Revenue, Orders); inconsistent dates break time-series grouping. |
| **Business Analysis / Research** | Outlier detection, distribution preservation, hypothesis sample size ($n \ge 30$) | Preserves valid empirical variance and verifies statistical power for parametric comparisons. |

---

## 4. Rule-Based Domain Detection Heuristics

Datasets are classified into business domains by matching normalized column names against targeted keyword dictionaries:
* **Finance**: `revenue`, `profit`, `ebitda`, `margin`, `cost`, `expense`, `tax`, `invoice`, `balance`, `ledger`, `asset`
* **Healthcare**: `patient`, `diagnosis`, `doctor`, `hospital`, `treatment`, `symptom`, `blood`, `dosage`, `glucose`
* **E-Commerce**: `order`, `cart`, `sku`, `product`, `shipping`, `checkout`, `discount`, `inventory`, `buyer`
* **Marketing**: `campaign`, `lead`, `click`, `ctr`, `impression`, `conversion`, `spend`, `cpa`, `cpc`, `bounce`
* **HR & Workforce**: `employee`, `salary`, `bonus`, `department`, `hire_date`, `job_title`, `tenure`, `payroll`
* **SaaS & Tech**: `mrr`, `arr`, `churn`, `subscription`, `plan`, `trial`, `renewal`, `seats`, `active_users`

Confidence is calculated as the proportion of keyword hits over total columns, bounded between 0.20 and 0.95.

---

## 5. Statistical Rules for EDA & Bivariate Comparisons

* **Minimum Group Size**: When comparing a numeric metric across categorical cohorts, groups with fewer than 5 observations ($n < 5$) are strictly excluded to avoid small-sample bias.
* **Correlations**: Both Pearson (linear) and Spearman rank (monotonic) coefficients are computed.
* **Outlier Fences**:
  $$\text{Lower Fence} = Q_1 - 1.5 \times \text{IQR}$$
  $$\text{Upper Fence} = Q_3 + 1.5 \times \text{IQR}$$
  $$\text{Z-Score Threshold} = |z| > 3.0$$

---

## 6. Decision Support Disclaimer

> [!IMPORTANT]
> All readiness verdicts, quality scores, and automated insights produced by DataLens AI are deterministic, rule-based decision support indicators. They do not constitute mathematical proof of model fitness or regulatory compliance. Users must verify domain-specific business assumptions before operational deployment.
