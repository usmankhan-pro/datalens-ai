import pandas as pd
import pytest

from src.quality.custom_validation import (
    evaluate_allowed_values_rule,
    evaluate_range_rule,
)


def test_range_validation_counts_only_non_missing_out_of_range_values():
    data = pd.DataFrame({"age": [17, 18, 45, 121, None]})

    result = evaluate_range_rule(data, "age", minimum=18, maximum=120)

    assert result["checked"] == 4
    assert result["invalid"] == 2
    assert result["invalid_indices"] == [0, 3]


def test_range_validation_rejects_invalid_rules():
    data = pd.DataFrame({"age": [18], "name": ["Ada"]})

    with pytest.raises(ValueError, match="Minimum cannot exceed"):
        evaluate_range_rule(data, "age", minimum=10, maximum=1)
    with pytest.raises(ValueError, match="must be numeric"):
        evaluate_range_rule(data, "name", minimum=0)


def test_allowed_values_validation_counts_unmatched_values():
    data = pd.DataFrame({"status": ["active", "inactive", "hold", None]})

    result = evaluate_allowed_values_rule(data, "status", ["active", "inactive"])

    assert result["checked"] == 3
    assert result["invalid"] == 1
    assert result["invalid_indices"] == [2]
