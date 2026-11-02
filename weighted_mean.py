"""Port of WeightedMean.m.

A robust "weighted mean": the data are sorted, every pair of neighbouring
values contributes its midpoint, and each midpoint is weighted by the inverse
of the gap between the two neighbours. Dense regions of the data (small gaps)
therefore dominate the estimate, while isolated values (outliers) carry
little weight.
"""

import numpy as np

# MATLAB: weights(weights == Inf) = 200;
# Weight given to a pair of identical values (gap 0). Measurements are rounded
# to 2 decimal places, so the largest weight of a non-zero gap is 1/0.01 = 100;
# 200 is deliberately above that.
MAX_WEIGHT = 200.0


def weighted_mean(x):
    """Return the gap-weighted mean of ``x`` (NaN values are ignored)."""
    # MATLAB: I = ~isnan(x); x = x(I);
    x = np.asarray(x, dtype=float).ravel()
    x = x[~np.isnan(x)]

    # FIX: MATLAB returns NaN (0/0) silently when fewer than two valid values
    # exist. Return NaN explicitly instead of triggering a divide warning.
    if x.size < 2:
        return np.nan

    # MATLAB: x = sort(x);
    x = np.sort(x)

    # MATLAB: pairWiseMean = (x(1:end-1)+x(2:end))/2;
    pair_wise_mean = (x[:-1] + x[1:]) / 2.0

    # MATLAB: weights = 1./(x(2:end) - x(1:end-1));
    gaps = x[1:] - x[:-1]
    with np.errstate(divide="ignore"):
        weights = 1.0 / gaps

    # MATLAB: weights(weights == Inf) = 200;
    # Identical neighbouring values (gap 0) give 1/0 = Inf; only those weights
    # are replaced with 200, exactly as in the original. This is intentional:
    # all measurements are rounded to 2 decimal places (0.01 resolution), so any
    # non-zero gap is >= 0.01 and its weight 1/gap is <= 100. A weight of 200
    # therefore always ranks identical values above every distinct pair.
    weights[np.isinf(weights)] = MAX_WEIGHT

    # MATLAB: WM = sum(pairWiseMean.*weights)/sum(weights);
    return float(np.sum(pair_wise_mean * weights) / np.sum(weights))
