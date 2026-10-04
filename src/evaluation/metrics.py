"""Small, dependency-free metrics for treatment-balance diagnostics."""

import math
from collections.abc import Sequence


def standardized_mean_difference(
    treated: Sequence[float], control: Sequence[float]
) -> float:
    """Return pooled-SD standardized mean difference (treated minus control).

    Inputs must be finite numeric observations with at least two values in each
    arm and non-zero pooled variance. For binary features, supply 0/1 values;
    the sample variances provide the pooled Bernoulli variance estimate.
    """
    if len(treated) < 2 or len(control) < 2:
        raise ValueError("Each treatment arm requires at least two observations")
    values = [*treated, *control]
    if any(not math.isfinite(value) for value in values):
        raise ValueError("Inputs must contain only finite values")

    mean_t = sum(treated) / len(treated)
    mean_c = sum(control) / len(control)
    var_t = sum((value - mean_t) ** 2 for value in treated) / (len(treated) - 1)
    var_c = sum((value - mean_c) ** 2 for value in control) / (len(control) - 1)
    pooled_sd = math.sqrt(
        ((len(treated) - 1) * var_t + (len(control) - 1) * var_c)
        / (len(treated) + len(control) - 2)
    )
    if pooled_sd == 0:
        raise ValueError("Pooled standard deviation is zero; SMD is undefined")
    return (mean_t - mean_c) / pooled_sd
