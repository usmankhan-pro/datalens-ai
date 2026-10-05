# Contributing to DataLens AI

Thanks for helping improve the platform.

## Project structure

- `app.py`: Streamlit entrypoint and navigation
- `core/`: analytical logic separated from UI code
- `ui/`: page renderers and theme layer
- `tests/`: regression tests and fixture coverage

## Adding a new detector

1. Add the detector implementation under the relevant `core/` package.
2. Keep the public API small and typed.
3. Return values in a consistent schema with `row_index`, `column`, `value`, `score`, and `method`.
4. Add unit tests proving expected behavior on a known dataset.
5. Update any page or summary logic that consumes results from the detector.

## Quality bar

- No fabricated numbers or fake UI metrics
- Use real computations from the current DataFrame
- Keep the UI thin; logic belongs in `core/`
- Run the relevant pytest targets before submitting changes
