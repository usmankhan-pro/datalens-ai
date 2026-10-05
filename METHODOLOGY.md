# Methodology

This document summarizes the analytic rules used throughout DataLens AI.

## Data quality score

The overall score is computed as:

$$
0.30 \times Completeness + 0.15 \times Uniqueness + 0.25 \times Validity + 0.20 \times Consistency + 0.10 \times AccuracyIndicator
$$

where each component is normalized to a 0-100 scale.

### Dimension definitions

- Completeness: $100 \times (1 - missing\_cells / total\_cells)$
- Uniqueness: $100 \times (1 - duplicate\_rows / total\_rows)$, with extra penalty for duplicate IDs
- Validity: $100 \times (1 - invalid\_values / checked\_values)$
- Consistency: penalizes mixed-type columns, inconsistent text formatting, mixed date formats, and constant columns
- Accuracy / Validity Indicator: outlier-adjusted score used as an indicator, not proof of real-world accuracy

### Severity thresholds

- Missing values: <5 LOW, 5-15 MEDIUM, 15-40 HIGH, >40 CRITICAL
- Duplicate rows: <1 LOW, 1-5 MEDIUM, 5-15 HIGH, >15 CRITICAL
- Invalid values: <1 LOW, 1-5 MEDIUM, 5-15 HIGH, >15 CRITICAL
- Outliers: <1 LOW, 1-3 MEDIUM, 3-7 HIGH, >7 CRITICAL

## Type inference

Columns are inferred in the following order on non-null values:

1. constant
2. boolean
3. numeric
4. datetime
5. id
6. categorical
7. text

This keeps the inference behavior consistent for mixed or ambiguous datasets.

## Statistical rules

- Descriptive statistics are computed for numeric columns only.
- Normality checks use Shapiro-Wilk for samples up to 5000 or D'Agostino K^2 otherwise.
- Confidence intervals for the mean use a 95% t-based calculation when $n \ge 30$.
- Correlation uses both Pearson and Spearman; the headline method depends on skewness and normality.
- Group comparisons require at least 5 observations per group.
- Outlier checks use IQR fences, z-score thresholds, and modified z-score thresholds.

## Privacy

The platform processes data in memory and never persists uploaded files to the application volume. Session isolation is managed through Streamlit session state.

## Deployment notes

The app is designed to run as a standard Streamlit application and can be served in a container or on a host environment with the dependencies from `requirements.txt` installed.
