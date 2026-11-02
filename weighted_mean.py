"""Port of WeightedMean.m.

A robust "weighted mean": the data are sorted, every pair of neighbouring
values contributes its midpoint, and each midpoint is weighted by the inverse
of the gap between the two neighbours. Dense regions of the data (small gaps)
therefore dominate the estimate, while isolated values (outliers) carry
little weight.
"""

import numpy as np

# MATLAB: weights(weights == Inf) = 200;
# Maximum weight a single neighbouring pair may receive.
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
    # FIX: the original only replaced *infinite* weights (identical values) with
    # 200, so a pair 0.001 apart got weight 1000 while two identical values got
    # only 200. A tie was weighted less than a near-tie. Capping every weight at
    # 200 gives the intended "identical values get the maximum weight" behaviour.
    # (For data whose resolution is coarser than 1/200 = 0.005 the result is
    # identical to the original.)
    weights = np.minimum(weights, MAX_WEIGHT)

    # MATLAB: WM = sum(pairWiseMean.*weights)/sum(weights);
    return float(np.sum(pair_wise_mean * weights) / np.sum(weights))
