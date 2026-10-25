# DataFlow Analytics

[![Python CI](https://github.com/usmankhan-pro/dataflow-analytics/actions/workflows/python-tests.yml/badge.svg)](https://github.com/usmankhan-pro/dataflow-analytics/actions/workflows/python-tests.yml)

DataFlow Analytics is a Streamlit application for inspecting, cleaning, and
analyzing tabular CSV and Excel data. It brings data quality checks, reviewable
cleaning operations, exploratory analysis, visualizations, and exports into a
single session-based workspace.

The application is designed to keep data decisions visible: cleaning changes
are previewed before approval, applied to a working copy, and recorded in an
audit history. Uploaded data is processed in memory and is not saved by the
application.

## Features

- **Dashboard:** dataset size, quality score, key findings, and workspace
  shortcuts.
- **Data quality:** a configurable 0–100 score across completeness, validity,
  consistency, uniqueness, and structural quality; validation checks, column
  profiles, findings, and recommendations.
- **Data cleaning:** preview and approve or reject duplicate removal, missing
  value handling, type conversion, text normalization, and outlier handling.
  Includes an operation history, undo, and reset.
- **Data visualization:** data-aware chart choices, variable controls, filters,
  and chart downloads.
- **Exploratory data analysis:** descriptive profiles, univariate and bivariate
  summaries, grouped analysis, correlations, and interactive charts where
  supported by the selected data.
- **Insights and recommendations:** observations derived from the current
  working data, with supporting evidence and limitations.
- **Reports and exports:** download cleaned data, cleaning history, quality
  results, EDA results, and assembled reports in supported formats.
- **Data source and settings:** preview and confirm CSV/XLSX/XLSM uploads,
  choose Excel worksheets, and review or reset the active workspace.

## Technology

- Python 3.11+ (CI runs on Python 3.12)
- Streamlit
- pandas and NumPy
- Plotly
- Matplotlib and Seaborn
- openpyxl
- pytest

Dependency versions and ranges are declared in [`requirements.txt`](requirements.txt)
and [`requirements-dev.txt`](requirements-dev.txt).

## Project structure

```text
.
├── .github/
│   └── workflows/
│       └── python-tests.yml       # GitHub Actions test workflow
├── .kilo/
│   └── agents/
│       └── data.md
├── .streamlit/
│   └── config.toml                # Application theme
├── config/
│   └── settings.py               # Quality thresholds and resource limits
├── data/
│   └── telco_churn.csv           # Bundled demonstration dataset
├── docs/
│   ├── methodology.md
│   └── reference-project-analysis.md
├── src/
│   ├── analysis/                 # Descriptive and relationship analysis
│   ├── cleaning/                 # Cleaning operations and audit pipeline
│   ├── data/                    # CSV/Excel loader and schema detection
│   ├── quality/                 # Scoring, validation, and findings
│   ├── reporting/               # Report generation and export helpers
│   ├── utils/                   # Shared formatting utilities
│   ├── visualization/           # Chart recommendations and builders
│   ├── ui.py                    # Streamlit workspaces
│   └── workspace.py             # Session-scoped dataset state
├── tests/                       # Unit and workflow regression tests
├── app.py                       # Streamlit entry point and legacy helpers
├── cleaning.py                  # Backwards-compatible cleaning helpers
├── eda.py                       # Backwards-compatible EDA utilities
├── plots.py                     # Backwards-compatible chart utilities
├── profiling.py                 # Backwards-compatible profiling utilities
├── LICENSE
├── README.md
├── requirements-dev.txt
└── requirements.txt
```

## Installation and run (Windows PowerShell)

Clone the repository after its GitHub rename is complete:

```powershell
git clone https://github.com/usmankhan-pro/dataflow-analytics.git
cd dataflow-analytics
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m streamlit run app.py
```

`requirements-dev.txt` installs the runtime dependencies and pytest. If
PowerShell blocks virtual-environment activation, run Streamlit through the
environment's Python executable instead:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

The app opens at the local URL printed by Streamlit, typically
`http://localhost:8501`.

## Using the application

1. Open **Dashboard** and upload a CSV or Excel workbook, or choose the bundled
   Telco churn demonstration dataset.
2. Review the preview and confirm the upload to make it the active dataset.
   Excel uploads support `.xlsx` and `.xlsm`; select the worksheet to load.
   CSV delimiter and encoding can be detected or selected in the upload UI.
3. Review the quality score and findings. Scores summarize configured
   heuristics; they are not a guarantee of correctness.
4. In **Data Cleaning**, select an operation, inspect its preview, and approve
   it to update the working copy. Approved operations can be undone or reset.
5. Explore charts, EDA summaries, and insights using the same working data.
6. Download available cleaned data, audit history, and reports from
   **Reports & Export**.

The sidebar provides eight workspaces: Dashboard, Data Quality, Data Cleaning,
Data Visualization, Exploratory Data Analysis (EDA), Insights & Recommendations,
Reports & Export, and Data Source & Settings.

## Testing

Run the test suite from the repository root:

```powershell
python -m pytest -q
```

The GitHub Actions workflow installs `requirements-dev.txt` and runs the same
test command on Python 3.12.

## Limitations

- Supported uploads are CSV, XLSX, and XLSM; JSON, Parquet, and database
  connections are not currently supported.
- Files are limited to 200 MB and 1,000,000 rows by the loader configuration.
- Processing is session-scoped and in memory. The application does not provide
  persistent storage, user authentication, or multi-user access controls.
- Quality scores and findings are rule-based indicators. They do not establish
  source accuracy, statistical validity, or suitability for a particular
  decision.
- Automatic type inference and statistical analysis can be affected by unusual
  schemas, small samples, or malformed source data. Review previews and results
  before relying on them.
- The app does not fabricate fields missing from an uploaded file; a
  single-column CSV remains a single-column dataset.

## Deployment

The application can be deployed using Streamlit Community Cloud:

1. Push the repository to GitHub after renaming it to
   `usmankhan-pro/dataflow-analytics`.
2. In Streamlit Community Cloud, create an app from that repository, select
   the `main` branch, and set the app entry point to `app.py`.
3. Deploy. Streamlit Cloud installs dependencies from `requirements.txt`.

No deployed app URL is configured in this repository. The application does not
require secrets for its current functionality; do not add credentials to the
repository.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
