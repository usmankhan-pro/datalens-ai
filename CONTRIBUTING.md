# Contributing to DataLens AI

Thank you for contributing to DataLens AI. Please follow our established architecture and quality guidelines.

---

## Architecture Guidelines

* **Pure Analytical Logic (`core/`)**: All computation belongs in `core/`. Modules must have clean, typed APIs, complete docstrings, and zero UI dependencies.
* **Thin Streamlit UI (`ui/pages/`)**: UI components must only orchestrate views, render charts, and invoke `core/` functions.
* **State Management (`core/utils/state.py`)**: All state resides in `DatasetBundle` within Streamlit's session state. The original dataset (`original_df`) is strictly immutable; modifications apply to `working_df` with snapshots saved to `history_stack` for undo.
* **Page Registration (`ui/pages/registry.py`)**: Pages are registered in `get_page_registry()` and `get_page_files()` following the goal-aware workflow.

---

## Quality Bar & Core Rules

1. **No Fabricated Numbers**: Every metric, percentage, correlation, and insight MUST be computed from the real DataFrame in memory.
2. **Deterministic & Explainable**: Rely on transparent, rule-based heuristics; no opaque black-box models.
3. **In-Memory Execution**: Do not persist or cache uploaded data to disk.
4. **Safety Classifications**:
   - `safe`: Non-destructive operations (trimming, deduplication, standardizing names/types).
   - `review`: Imputation or subset deduplication.
   - `risky`: Irreversible data removal (capping/removing outliers, dropping columns).

---

## Adding a New Cleaning Operation

1. Implement the transformation function in [core/cleaning/pipeline.py](file:///c:/Users/usman/OneDrive/Desktop/DataLensAi/core/cleaning/pipeline.py) returning `Tuple[pd.DataFrame, int]`.
2. Register its metadata in `OPERATION_SPECS` (`stage`, `risk`, `label`, `desc`).
3. Add dispatch handling in `_dispatch_operation()`.
4. Add corresponding code generation support in [core/export/script_generator.py](file:///c:/Users/usman/OneDrive/Desktop/DataLensAi/core/export/script_generator.py).
5. Add unit tests covering the operation in [tests/test_stage2_cleaning_pipeline.py](file:///c:/Users/usman/OneDrive/Desktop/DataLensAi/tests/test_stage2_cleaning_pipeline.py).

---

## Running the Test Suite

Always execute the complete test suite before submitting pull requests:

```bash
python -m pytest -v
```
