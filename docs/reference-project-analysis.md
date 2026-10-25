# Reference Project Analysis and DataFlow Analytics Plan

## Scope and evidence

The reference archive (`Data-Analysis-Automation-main.zip`) contains only
`README.md`, `app.py`, and `requirements.txt`; it has no separate pages,
components, analysis modules, or tests. Its features below are verified in
`app.py`, not inferred from README claims.

The checked-out DataFlow Analytics repository is the implementation target. The
provided project archive is not the same snapshot: it bundles `.git`, a
virtual environment, and caches, while its application source is the older
root-level implementation and it does not contain the checked-out `src/`
modules. This analysis and the code changes use the current worktree, not that
stale archive copy.

## Reference application

- **Navigation and state:** A sidebar radio chooses Home, EDA, Data
  Visualization, Data Preprocessing, or Machine Learning. Each work area
  renders its own uploader; the uploaded frame is not a shared cross-page
  workflow.
- **Upload and errors:** EDA and visualization read CSV, TXT, and Excel
  (Excel only in EDA/visualization); preprocessing and clustering read CSV/TXT.
  All paths use `pandas.read_csv` with its default comma delimiter. Each page
  wraps its work in a broad exception handler and displays an error in the UI.
- **EDA:** Shows a preview, missing-value counts, and checkbox-controlled
  shape, columns, summary statistics, selected columns, value counts, and a
  numeric-only correlation heatmap. Missing numeric values are filled with
  means and categorical values with modes when requested.
- **Visualization:** Offers value-count bars and basic area, bar, line, or
  scatter plots from the first two selected columns. It does not validate
  suitability of selected column types before plotting.
- **Preprocessing:** Offers missing-value filling, label encoding, and
  standard scaling. The displayed encoded/scaled frames are separate results;
  the download serializes `df`, so it does not include those transformations.
- **Clustering:** Label-encodes every column, runs two-component PCA and
  KMeans, displays clusters and numeric summaries, and offers a CSV download.
  The code does not validate data size, nulls, or PCA/KMeans constraints first.
- **Presentation:** A CSS block attempts to style the Streamlit page and the
  sidebar radio provides a simple task-oriented navigation pattern.
- **Documentation vs. implementation:** The README broadly describes the
  above tasks but does not document the limitations just listed. No tests are
  included in the archive. No application run was attempted because
  scikit-learn, a required reference dependency, is not installed in the
  available Python environment.

## DataFlow Analytics in the current worktree

DataFlow Analytics is a Streamlit application with a persistent sidebar and
dedicated Dashboard, Data Quality, Data Cleaning, Data Visualization, EDA,
Insights & Recommendations, Reports & Export, and Data Source & Settings
workspaces.
`read_table` supports CSV and Excel in memory; the UI also offers a bundled
Telco demo. The current architecture retains tested root-level compatibility
modules (`cleaning.py`, `eda.py`, `plots.py`, and `profiling.py`) and adds
domain modules under `src/` for schema detection, quality, cleaning,
analysis, visualization, and reporting.

Verified capabilities include a five-dimension quality score, validation and
ranked findings, column profiling, user-selected cleaning with an audit
pipeline and undo/reset, type-aware EDA and chart recommendations, evidence-
based insights, and CSV/Excel/report downloads. The current suite had 71
passing tests before the regression fix.

The app exposes quality scoring and ranked issue findings, but several
implemented backend APIs are not currently wired into its tabs: the complete
`run_all_validations` report, schema detector, univariate/multivariate helper
APIs, automatic per-column chart recommendation function, and assembled
quality/cleaning/full report builders. The Export tab does provide cleaned
data, a cleaning log, and a quality-dimension CSV. Code presence in `src/`
should not be confused with a user-accessible workflow.

### Reported CSV and EDA behavior

The supplied `subs.csv` contains the header `Subscribers gained` followed by
365 newline-separated integer values. It has no commas, semicolons, or other
field separators, so pandas correctly loads it as 365 rows and one column.
That is the file's actual shape, not a parser defect; a date column cannot be
inferred from the file.

The one-column dataset did expose an EDA defect. The modern EDA always created
two bivariate selectors; the second selector had no options and produced
`None`. `recommend_pair_chart` indexed `data[None]`, which was reproduced as
`KeyError: None`. The current fix presents an explanatory message instead and
keeps univariate analysis available. The selector helper also returns no
recommendations for an unselected or absent pair instead of raising a pandas
`KeyError`.

### Additional target risks

- `config/settings.py` defines upload/row/time resource limits, but the
  current loader does not enforce them. Large inputs can therefore consume
  more time and memory than those settings imply.
- `CleaningPipeline.to_result()` sets `source_immutable` using
  `self._working.equals(self._source) or True`, which always reports `True`.
  That flag is not valid evidence of immutability, even though individual
  cleaning operations are written to work on copies.
- The README says CSV delimiter detection is automatic, but
  `read_table` calls `pandas.read_csv` without delimiter inference. A
  semicolon-delimited multi-column CSV can therefore appear as one column.
  This does not explain `subs.csv`, whose source contains only one field per
  row.

## Comparison and priorities

| Area | Reference | DataFlow Analytics | Assessment |
|---|---|---|---|
| Workflow | Five radio-selected activities, separate uploads | Shared dataset across eight dedicated workspaces | Keep the shared workflow; it prevents repeated uploads and supports its cleaning-to-export path. |
| Upload | CSV/TXT default parsing; Excel in two areas | CSV and Excel loaded in memory with normalization and clear upload errors | Keep the target loader; do not invent columns or dates for single-field files. |
| Cleaning | Mean/mode fill and basic label encoding/scaling | Preview-driven, audited, user-controlled cleaning with undo/reset | Target is substantially safer and more complete; preserve it. |
| EDA | Checkbox summaries and numeric heatmap | Profiles, bivariate chart recommendations, correlations, and insights | Preserve the richer target; guard small/one-column inputs. |
| Charts | Four basic manually selected Matplotlib plots | Type-aware static and Plotly chart builders with availability reasons | Preserve type-aware recommendations; reuse reference's direct task navigation only if future user testing supports it. |
| ML | Label encoding, PCA, KMeans | No corresponding clustering workflow is exposed in the current tabs | Potential future feature, not copied: reference implementation lacks safe type handling and validation. |
| Tests | None | 71 tests covering loading, cleaning, EDA, charts, and exports | Keep regression tests as part of the workflow. |

### Reusable ideas

1. Present tasks in a clear navigation structure and make available actions
   visible.
2. Show data previews and concise results adjacent to the selected operation.
3. Explain why an operation cannot be offered, rather than failing in a chart
   library or pandas.
4. Keep exports close to the operation that produced the result.

DataFlow Analytics already implements these ideas more safely in most areas. The
reference's automatic mean/mode imputation, unvalidated encoders, broad
exception handling, and clustering implementation should not be copied.

## Implementation plan and file-by-file changes

| Priority | File | Change |
|---|---|---|
| P0 | `app.py` | Skip bivariate selectors for fewer than two columns and explain that univariate analysis remains available. |
| P0 | `src/visualization/chart_selector.py` | Accept an absent selection and return no recommendations if either requested column is not present. |
| P0 | `tests/test_stage1_upload.py` | Assert that a header plus 365 single-field records loads as 365×1 without fabricated columns. |
| P0 | `tests/test_stage3_eda.py` | Cover absent bivariate selections and run the Streamlit app with a one-column frame to prevent recurrence of `KeyError: None`. |
| P0 | `docs/reference-project-analysis.md` | Record the evidence-based comparison, archive discrepancy, implemented findings, adoption choices, and acceptance criteria. |

### Follow-up recommendations (not part of this focused fix)

1. **P1 — Align delivered artifacts:** regenerate the target ZIP from the
   current checkout and exclude `.git`, virtual environments, and caches.
2. **P2 — Enforce resource limits:** use configured file-size and row limits
   in the loader and communicate rejected files clearly; define how the
   processing-time limit is measured before enforcing it.
3. **P2 — Clarify delimiter handling:** the current target loader, like the
   reference loader, uses pandas' default comma parsing despite README
   wording. If multi-column semicolon/tab-delimited inputs are in scope, add
   explicit delimiter selection or validated detection with tests; do not
   treat a true single-field file as malformed.
4. **P3 — Correct the immutability status:** replace the always-true result
   flag with a meaningful assertion/status and test it if consumers depend on
   `CleaningResult.source_immutable`.
5. **P4 — Consolidate legacy and modern paths:** assess usage before removing
   root-level compatibility modules; avoid a broad rewrite while both paths
   still have tests or callers.
6. **P5 — Consider machine learning separately:** if clustering is desired,
   design it as an opt-in workflow with numeric/categorical preprocessing,
   missing-data handling, dimensionality constraints, and tests rather than
   copying the reference implementation.

## Testing strategy and acceptance criteria

- Run targeted tests for upload shape, chart recommendation edge cases, and
  Streamlit EDA with one column.
- Run the full existing `pytest -q` suite to protect current upload, cleaning,
  EDA, chart, and export behavior.
- Confirm the 365-value fixture yields exactly 365 rows and the original
  single header; no separator or date is fabricated.
- Confirm the app has no uncaught Streamlit exception for one-column data,
  continues to provide univariate views, and explains why bivariate analysis
  is unavailable.
- Confirm existing two-column chart recommendation and rendering tests
  remain unchanged and pass.
- Do not claim a reference runtime test: its required scikit-learn dependency
  is unavailable in this environment.
