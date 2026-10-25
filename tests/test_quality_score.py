import pandas as pd

from config.settings import QUALITY_WEIGHTS
from src.quality.quality_score import compute_quality_score


def test_quality_score_matches_documented_weighted_dimension_formula():
    data = pd.DataFrame(
        {
            "amount": [1.0, 2.0, None],
            "category": ["North", "north", "South"],
            "constant": [7, 7, 7],
            "identifier": ["a", "b", "c"],
        }
    )
    original = data.copy(deep=True)

    result = compute_quality_score(data)
    scores = {dimension.name: dimension.score for dimension in result.dimensions}
    expected = round(
        sum(
            scores[name] * weight
            for name, weight in (
                ("Completeness", QUALITY_WEIGHTS.completeness),
                ("Validity", QUALITY_WEIGHTS.validity),
                ("Consistency", QUALITY_WEIGHTS.consistency),
                ("Uniqueness", QUALITY_WEIGHTS.uniqueness),
                ("Structural quality", QUALITY_WEIGHTS.structural),
            )
        )
        / 100,
        2,
    )

    assert scores == {
        "Completeness": 91.67,
        "Validity": 100.0,
        "Consistency": 50.0,
        "Uniqueness": 100.0,
        "Structural quality": 75.0,
    }
    assert result.overall_score == expected == 84.17
    assert 0 <= result.overall_score <= 100
    assert data.equals(original)


def test_quality_score_for_empty_data_is_bounded_and_explains_exclusions():
    result = compute_quality_score(pd.DataFrame({"value": pd.Series(dtype="float64")}))

    assert 0 <= result.overall_score <= 100
    assert "Completeness" in result.excluded_dimensions
    assert "Uniqueness" in result.excluded_dimensions
