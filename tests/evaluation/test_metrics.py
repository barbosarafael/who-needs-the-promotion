import math

import pytest

from src.evaluation.metrics import standardized_mean_difference


def test_smd_direction_and_scale():
    assert standardized_mean_difference([2, 4, 3], [0, 2, 1]) == pytest.approx(2.0)
    assert standardized_mean_difference([0, 1], [1, 0]) == 0.0


@pytest.mark.parametrize(
    ("treated", "control"),
    [([1], [0, 1]), ([1, 1], [0, 0]), ([math.nan, 1], [0, 1])],
)
def test_smd_rejects_undefined_inputs(treated, control):
    with pytest.raises(ValueError):
        standardized_mean_difference(treated, control)
