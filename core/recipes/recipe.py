"""Cleaning Recipe serialization, deserialization, and execution for DataLens AI.

Enables saving cleaning pipelines as declarative JSON recipes and reusing them
across matching datasets.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
import pandas as pd

from core.cleaning.pipeline import apply_operation
from core.utils.state import TransformRecord


@dataclass
class CleaningRecipe:
    """Declarative recipe capturing a series of cleaning operations."""
    name: str
    created_at: str
    description: str
    target_columns: List[str]
    steps: List[Dict[str, Any]]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_json(self, indent: int = 2) -> str:
        """Serialize recipe to JSON string."""
        return json.dumps(asdict(self), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> CleaningRecipe:
        """Construct a CleaningRecipe from JSON string."""
        data = json.loads(json_str)
        return cls(
            name=data.get("name", "Unnamed Recipe"),
            created_at=data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            description=data.get("description", ""),
            target_columns=data.get("target_columns", []),
            steps=data.get("steps", []),
            metadata=data.get("metadata", {}),
        )


def save_recipe(
    history: Sequence[Any],
    name: str = "custom_cleaning_recipe",
    target_columns: Optional[List[str]] = None,
    description: str = "",
) -> str:
    """
    Serialize an audit log history into a reusable JSON cleaning recipe.

    Args:
        history: Sequence of TransformRecord objects or dictionaries.
        name: Recipe title.
        target_columns: Columns the recipe expects to act upon.
        description: Plain-language summary of what the recipe does.

    Returns:
        Formatted JSON string.
    """
    steps = []
    cols_accum: set = set(target_columns or [])

    for idx, item in enumerate(history, start=1):
        if isinstance(item, dict):
            op = item.get("operation", "")
            params = item.get("params", {})
            columns = item.get("columns", [])
            stage = item.get("stage", "cleaning")
            risk = item.get("risk", "safe")
        else:
            op = getattr(item, "operation", "")
            params = getattr(item, "params", {})
            columns = getattr(item, "columns", [])
            stage = getattr(item, "stage", "cleaning")
            risk = getattr(item, "risk", "safe")

        if columns:
            cols_accum.update(columns)

        steps.append({
            "step": idx,
            "operation": op,
            "stage": stage,
            "risk": risk,
            "columns": columns,
            "params": params,
        })

    recipe = CleaningRecipe(
        name=name,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        description=description or f"Auto-generated recipe with {len(steps)} cleaning step(s).",
        target_columns=sorted(list(cols_accum)),
        steps=steps,
        metadata={"version": "1.0", "generator": "DataLens AI"},
    )

    return recipe.to_json()


def load_recipe(json_str: str) -> CleaningRecipe:
    """Parse and validate JSON string into a CleaningRecipe."""
    return CleaningRecipe.from_json(json_str)


def validate_recipe_compatibility(recipe: CleaningRecipe, df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Check if a recipe is compatible with the target DataFrame schema.

    Returns:
        Tuple of (is_compatible, list_of_warning_messages).
    """
    if df is None or df.empty:
        return False, ["Target DataFrame is empty."]

    warnings = []
    df_cols = set(df.columns)
    missing_cols = [c for c in recipe.target_columns if c not in df_cols]

    if missing_cols and len(missing_cols) == len(recipe.target_columns) and len(recipe.target_columns) > 0:
        return False, [f"None of the recipe target columns exist in dataset. Missing: {', '.join(missing_cols[:5])}"]

    if missing_cols:
        warnings.append(f"Some target columns are missing in dataset: {', '.join(missing_cols[:5])}. Affected steps will be skipped or adapted.")

    return True, warnings


def apply_recipe(
    df: pd.DataFrame,
    recipe: CleaningRecipe,
    stop_on_error: bool = False,
) -> Tuple[pd.DataFrame, List[TransformRecord], List[str]]:
    """
    Apply all operations from a recipe sequentially to a DataFrame copy.

    Args:
        df: Target DataFrame (never mutated).
        recipe: CleaningRecipe instance.
        stop_on_error: If True, raise exception on step failure; else skip with warning.

    Returns:
        Tuple of (cleaned_df, applied_records, warning_messages).
    """
    working_df = df.copy()
    applied_records: List[TransformRecord] = []
    warnings: List[str] = []

    for step in recipe.steps:
        op = step.get("operation")
        params = step.get("params", {})
        cols = step.get("columns", [])
        stage = step.get("stage", "cleaning")
        risk = step.get("risk", "safe")

        # Skip step if specific columns required do not exist in current dataframe
        if cols and not any(c in working_df.columns for c in cols) and op not in ("snake_case_columns", "drop_empty_rows", "drop_empty_columns"):
            warnings.append(f"Skipped step '{op}': columns {cols} not found.")
            continue

        try:
            res = apply_operation(working_df, op, params)
            working_df = res["df"]
            applied_records.append(
                TransformRecord(
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    operation=op,
                    columns=cols,
                    params=params,
                    rows_affected=res["rows_affected"],
                    stage=stage,
                    risk=risk,
                )
            )
        except Exception as e:
            if stop_on_error:
                raise
            warnings.append(f"Step '{op}' failed with error: {str(e)}. Proceeding to next step.")

    return working_df, applied_records, warnings
