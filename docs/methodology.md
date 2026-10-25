# DataLens AI — Methodology

This document explains the quality score formula, dimension weights, missing-data handling, duplicate detection, outlier methods, and limitations of the DataLens AI analysis engine.

---

## 1. Quality Score

### 1.1 Overall Formula

The quality score is a weighted average of five dimension scores, each measured from the dataset's properties:

```
Overall Score = SUM(dimension_score * dimension_weight) / SUM(applicable_weights)
```

Only dimensions that can be assessed are included. If a dimension cannot be assessed (e.g., completeness on an empty dataset), its weight is excluded and the remaining weights are renormalized proportionally.

The result is clamped to [0, 100] and rounded to 2 decimal places.

### 1.2 Dimension Weights (configurable)

| Dimension | Default Weight | Rationale |
|-----------|---------------|-----------|
| Completeness | 25% | Missing data directly reduces usable information and can bias analysis. |
| Validity | 25% | Values stored in the wrong type (e.g., numbers as text) prevent correct computation. |
| Consistency | 20% | Inconsistent formatting (case, spacing) leads to incorrect grouping and aggregation. |
| Uniqueness | 15% | Duplicate rows inflate counts and can bias models. |
| Structural Quality | 15% | Empty, constant, or duplicate-named columns indicate schema problems. |

Weights sum to 100%. They are product conventions, not scientific standards, and can be adjusted in `config/settings.py`.

### 1.3 Dimension Details

#### Completeness

- **Numerator:** non-missing cells
- **Denominator:** total cells (rows × columns)
- **Score:** (non-missing / total) × 100
- **Missing definition:** `NaN`, `None`, `pd.NA`, and blank/whitespace-only strings (after normalization)
- **Severity:** HIGH (>=50% missing), MEDIUM (>=20%), LOW (>0%), NONE (0%)
- **Limitation:** Blank strings and placeholders are only treated as missing if they were normalized during loading. Otherwise they count as present.

#### Validity

- **Numerator:** text columns with expected value types
- **Denominator:** total text columns
- **Score:** (valid / total_text) × 100
- **Detection:** A text column is flagged if >= 80% of sampled non-null values (up to 500 rows) parse as numbers (numeric-as-text) or dates (date-as-text).
- **Severity:** based on percentage of invalid text columns
- **Limitation:** Detection is based on a sample of up to 500 rows per column. Type mismatches in unsampled rows may be missed.

#### Consistency

- **Numerator:** text columns without case/formatting inconsistencies
- **Denominator:** total text columns
- **Score:** (consistent / total_text) × 100
- **Detection:** A column is inconsistent if it has more distinct raw values than distinct casefolded (lowercased, stripped) values — indicating the same logical value appears in multiple forms (e.g., "New York", "new york", "NY").
- **Severity:** based on percentage of inconsistent text columns
- **Limitation:** Only detects case/formatting inconsistencies within text columns. Cross-column or semantic inconsistencies are not measured.

#### Uniqueness

- **Numerator:** unique rows (total − exact duplicates)
- **Denominator:** total rows
- **Score:** (unique / total) × 100
- **Detection:** Exact row duplicates using `pandas.DataFrame.duplicated()`.
- **Severity:** HIGH (>10% duplicates), MEDIUM (>5%), LOW (>0%), NONE (0%)
- **Limitation:** Measures exact row duplicates only. Repeated values in a single column (e.g., many customers from the same city) are legitimate and not penalized. Near-duplicates are not detected.

#### Structural Quality

- **Numerator:** structurally sound columns (total − structural issues)
- **Denominator:** total columns
- **Score:** (sound / total) × 100
- **Detection:**
  - Empty column: all values are null
  - Constant column: one distinct non-null value across all rows
  - Duplicate column name: name appears more than once
- **Severity:** based on percentage of columns with issues
- **Limitation:** Constant columns with a single meaningful value (e.g., a fixed treatment flag) are flagged even when intentional.

### 1.4 Interpretation Bands

| Score Range | Label | Meaning |
|-------------|-------|---------|
| 85–100 | Excellent | Very few quality issues; suitable for most analysis without extensive cleaning. |
| 70–84 | Good | Generally sound but some issues should be reviewed before analysis. |
| 50–69 | Needs Improvement | Several issues that may affect results if unaddressed. |
| 0–49 | Poor | Significant issues; analysis results may be unreliable without substantial cleaning. |

These thresholds are product conventions, not industry standards.

### 1.5 Small Dataset Warning

Scores on very small datasets (fewer than 30 rows) may be unstable. A single missing value or duplicate row can shift the score substantially. Interpret scores on small datasets with caution.

---

## 2. Missing-Data Handling

### 2.1 Detection

Missing values are detected as:
- `NaN`, `None`, `pd.NA` (pandas null)
- Empty strings and whitespace-only strings (after normalization during loading)
- Configured placeholders: `N/A`, `NA`, `null`, `none`, `nan`, `unknown`, `missing`, `-`, `--`, `` (empty string)

### 2.2 Imputation Strategies (user-selected per column)

| Strategy | Applicable to | Description |
|----------|--------------|-------------|
| Leave unchanged | All | No action taken |
| Drop rows | All | Remove rows with missing values in this column |
| Mean | Numeric | Fill with column mean |
| Median | Numeric | Fill with column median |
| Mode | All | Fill with most frequent value |
| Custom | All | Fill with user-specified value |
| Missingness indicator | All | Add boolean column flagging missing rows |

### 2.3 Rules

- Missing values are never imputed without explicit user approval.
- Each column can have a different strategy; no universal imputation is applied.
- Before/after statistics are recorded in the audit trail.
- Invalid placeholder values that cannot be converted during type conversion are disclosed, not silently dropped.

---

## 3. Duplicate Detection

### 3.1 Exact Duplicate Rows

Detected using `pandas.DataFrame.duplicated()` across all columns (or user-selected subset). The user chooses which occurrence to keep ("first" or "last").

### 3.2 Repeated Values in a Column

Repeated values in an individual column (e.g., multiple customers from "Boston") are **not** treated as duplicates. They are legitimate data and are not penalized in the uniqueness score.

### 3.3 Business-Key Duplicates

Users can select a subset of columns to identify potential business-key duplicates (e.g., same customer ID appearing multiple times). This is a manual inspection step, not automatic removal.

---

## 4. Outlier Detection

### 4.1 IQR-Based Method

- Q1 = 25th percentile, Q3 = 75th percentile
- IQR = Q3 − Q1
- Lower fence = Q1 − 1.5 × IQR
- Upper fence = Q3 + 1.5 × IQR
- Values outside the fences are outliers
- Multiplier is configurable (default: 1.5)

### 4.2 Z-Score-Based Method

- Z = (value − mean) / standard deviation
- Values with |Z| > threshold are outliers
- Threshold is configurable (default: 3.0)
- Only meaningful for approximately normal distributions

### 4.3 Actions (user-selected)

| Action | Description |
|--------|-------------|
| Ignore | No change |
| Cap | Clip values to the fences |
| Remove | Drop outlier rows |
| Flag | Add boolean outlier indicator column |

### 4.4 Limitations

- Outliers are statistical anomalies, not necessarily errors.
- Domain knowledge is required to distinguish errors from legitimate extreme values.
- No outliers are removed by default.

---

## 5. Type Detection

### 5.1 Inferred Types

| Type | Detection Rule |
|------|---------------|
| Numeric | Pandas numeric dtype (int, float) |
| Datetime | Pandas datetime64 dtype |
| Numeric string | Text column where >= 80% of sampled values parse as numbers |
| Date string | Text column where >= 90% of sampled values parse as dates |
| Categorical | Text column that doesn't match numeric or date patterns |
| Empty | All values are null |

### 5.2 Identifier Detection

A column is flagged as an identifier candidate if:
- Its name contains hints like "id", "key", "code", "uid", "uuid"
- All non-null values are unique

Identifier columns are excluded from default correlation matrices and meaningful statistical summaries.

### 5.3 Safe Conversion

- Invalid values that cannot be converted become missing and are counted/disclosed.
- Leading zeros in identifier columns are preserved by keeping them as strings.
- Users explicitly choose target types; no automatic conversion without approval.

---

## 6. Correlation Analysis

### 6.1 Methods

- **Pearson:** Linear relationship between two numeric variables. Sensitive to outliers.
- **Spearman:** Monotonic relationship based on ranked values. More robust to outliers.

### 6.2 Missing-Data Handling

Pairwise complete observations: each correlation coefficient is computed using only rows where both variables are non-null.

### 6.3 Limitations

- Correlation does not imply causation.
- Small samples produce unstable coefficients.
- Restricted ranges attenuate correlations.
- Identifier columns are excluded from the default matrix.

---

## 7. Limitations

1. **Score is not accuracy.** A high quality score does not prove the dataset is accurate, unbiased, representative, or suitable for every analysis. Fitness for purpose depends on the analytical objective.

2. **In-memory processing.** Datasets are processed entirely in memory. Very large datasets may exceed available RAM.

3. **Sample-based detection.** Type mismatch and date detection use samples of up to 500 rows per column. Issues in unsampled rows may be missed.

4. **No cross-column validation.** The engine does not validate cross-column business rules (e.g., "end date must be after start date") unless explicitly configured.

5. **No LLM dependency.** All analysis is deterministic and local. No external AI API is used, so no fabricated metrics can appear.

---

## 8. Reproducibility

- Identical inputs and settings always yield identical scores.
- All calculations use explicit missing-data policies (pairwise complete for correlations, listwise for most other metrics).
- All weights, thresholds, and parameters are configurable in `config/settings.py`.
- The audit trail records every cleaning operation with parameters, before/after statistics, and timestamps.
