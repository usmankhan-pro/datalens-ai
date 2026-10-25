# DataLens AI

**Automated Dataset Quality Assessment, Data Cleaning, and Exploratory Data Analysis Platform**

Upload a CSV or Excel file, understand its quality score, inspect and correct data issues safely, explore relevant variables, discover evidence-backed insights, and export reproducible results — all through a clear and reliable Streamlit interface. Data stays in memory; nothing is written to disk.

---

## Problem Statement

Analysts spend most of their time cleaning and understanding data rather than analyzing it. DataLens AI automates the repetitive parts — profiling, quality scoring, issue detection, cleaning, and EDA — while keeping every analytical decision transparent and user-controlled. Nothing is applied automatically without approval.

---

## Key Features

| Stage | What you can do |
|-------|----------------|
| **Upload** | Drag-and-drop CSV or Excel (XLSX/XLSM). See file name, size, rows, columns, detected format, and a preview. |
| **Validate** | Clear error messages for empty, malformed, or unreadable files. Duplicate column names and all-empty columns are flagged. |
| **Quality Score** | Transparent 0–100 score across five dimensions: Completeness, Validity, Consistency, Uniqueness, Structural Quality. Configurable weights. |
| **Column Profiling** | Per-column statistics for numeric, categorical, datetime, boolean, and identifier-like columns. |
| **Cleaning Studio** | Preview-then-apply cleaning: duplicates, missing values, type conversion, text cleaning, outlier handling. Full audit trail with undo/reset. |
| **EDA** | Univariate, bivariate, and multivariate analysis with Plotly charts. Automatic chart selection based on column types. |
| **Insights** | Evidence-backed observations with severity, recommended actions, and limitations. |
| **Export** | Download cleaned data (CSV/Excel), cleaning audit log, quality report, and before/after comparison. |

---

## Technology Stack

- **Python 3.10+**
- **Streamlit** — application interface
- **pandas** — data manipulation
- **NumPy** — numerical computing
- **matplotlib / seaborn** — static charts (legacy visualizations)
- **Plotly** — interactive charts (new EDA visualizations)
- **openpyxl** — Excel read/write
- **pytest** — testing

---

## Architecture

```
DataLensAI/
├── app.py                      # Streamlit application entry point
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Test dependencies
├── README.md                   # This file
├── .gitignore
├── LICENSE
├── config/
│   └── settings.py             # Quality weights, thresholds, resource limits
├── data/
│   └── telco_churn.csv         # Telco churn demo dataset
├── docs/
│   └── methodology.md          # Quality score formula and methods
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   └── schema_detector.py  # Column type and schema detection
│   ├── quality/
│   │   ├── __init__.py
│   │   ├── quality_score.py    # 0-100 quality scoring engine
│   │   ├── validation.py       # Validation rules and checks
│   │   └── issue_detection.py  # Structured quality findings
│   ├── cleaning/
│   │   ├── __init__.py
│   │   ├── audit.py            # Audit trail record types
│   │   ├── missing_values.py   # Missing-value detection and imputation
│   │   ├── duplicates.py       # Duplicate-row detection and removal
│   │   ├── data_types.py       # Type detection and safe conversion
│   │   ├── outliers.py         # IQR and Z-score outlier detection
│   │   ├── text_cleaning.py    # Text normalization and cleaning
│   │   └── cleaning_pipeline.py# Orchestrated cleaning with undo/reset
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── descriptive.py      # Dataset and column profiles
│   │   ├── univariate.py       # Single-column summaries
│   │   ├── bivariate.py        # Two-column analysis
│   │   ├── multivariate.py     # Correlation matrix, pivots, grouped summaries
│   │   ├── correlation.py      # Pearson and Spearman correlations
│   │   └── recommendations.py  # Evidence-backed insights and recommendations
│   ├── visualization/
│   │   ├── __init__.py
│   │   ├── charts.py           # Plotly chart builders
│   │   └── chart_selector.py   # Automatic chart recommendation
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── report_generator.py # Report assembly
│   │   └── export_manager.py   # Download-ready export bytes
│   └── utils/
│       ├── __init__.py
│       └── formatting.py       # Display formatting helpers
├── tests/
│   ├── test_loader.py
│   ├── test_profiling.py
│   ├── test_quality_score.py
│   ├── test_cleaning.py
│   └── test_analysis.py
├── sample_data/
└── docs/
    └── methodology.md
```

---

## Installation

### Windows PowerShell

```powershell
# Create and activate virtual environment
py -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

# Launch the application
streamlit run app.py
```

### macOS / Linux

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt

# Launch the application
streamlit run app.py
```

---

## Supported File Formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| CSV | `.csv` | UTF-8, auto delimiter detection, blank strings normalized to missing |
| Excel | `.xlsx`, `.xlsm` | First worksheet, `openpyxl` engine |

---

## Sample Workflow

1. **Upload** a CSV or Excel file, or click "Use demo data (Telco churn)".
2. **Overview** — Review row counts, column dtypes, missing values, duplicates, memory usage, and sample rows.
3. **Quality** — View the 0–100 quality score, dimension breakdown, and ranked issues.
4. **Cleaning Studio** — Preview and apply cleaning operations one at a time. Use Undo/Reset to experiment safely.
5. **EDA** — Explore distributions, correlations, and bivariate relationships with interactive Plotly charts.
6. **Insights** — Read evidence-backed observations with recommended actions.
7. **Export** — Download the cleaned dataset, cleaning audit log, and quality report.

---

## Quality Score

The score is 0–100, computed as a weighted average of five dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| Completeness | 25% | Percentage of non-missing cells |
| Validity | 25% | Text columns storing numeric or date values |
| Consistency | 20% | Case and formatting inconsistencies in text columns |
| Uniqueness | 15% | Percentage of non-duplicate rows |
| Structural Quality | 15% | Empty, constant, or duplicate-named columns |

Interpretation bands: **Excellent** (>=85), **Good** (>=70), **Needs Improvement** (>=50), **Poor** (<50).

Weights and thresholds are configurable in `config/settings.py`. A high score does **not** prove accuracy, bias-freedom, or fitness for a specific analytical objective.

---

## Data-Cleaning Methodology

- **Source data is immutable.** All cleaning works on a managed working copy.
- **Preview before apply.** Every operation shows before/after statistics and requires confirmation.
- **Audit trail.** Each operation records: step, column, operation, rows affected, parameters, before/after stats, success status, warnings, and timestamp.
- **Undo/Reset.** Revert to any previous state or restore the original data.
- **No automatic imputation.** Missing values are never filled without user-selected strategy per column.
- **No automatic outlier removal.** Outliers are flagged; the user chooses cap, remove, flag, or ignore.

---

## Testing

```powershell
pytest -q
```

Tests cover: clean datasets, missing values, duplicate rows, repeated legitimate values, incorrect numeric/datetime values, empty datasets, duplicate column names, mixed data types, outliers, small datasets, correlation with missing values, invalid uploads, and export round-trips.

---

## Privacy Considerations

- All data is processed in memory only.
- Uploaded datasets are not written to disk.
- No data is sent to external APIs or services.
- No credentials or secrets are stored in source code.
- The application works entirely offline.

---

## Future Improvements

- Larger dataset support (chunked processing, sampling)
- Additional file formats (JSON, Parquet, database connections)
- Reusable cleaning pipelines (save/load configurations)
- Optional AI-generated explanations (local LLM, opt-in)
- Multi-user deployment with authentication
- Scheduled reporting and automated data quality monitoring

---

## License

MIT License. See `LICENSE` for details.
