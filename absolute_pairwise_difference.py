"""Port of AbsolutePairwiseDifference.m.

Robust scale estimator (the Rousseeuw-Croux "Sn" estimator):
    APD = 1.1926 * median_i( median_{j != i} |x_i - x_j| )
The constant 1.1926 makes APD a consistent estimate of the standard deviation
for normally distributed data, so it can be used in place of ``sigma``.
"""

import numpy as np

# MATLAB: APD = 1.1926*median(M);
SN_CONSISTENCY_CONSTANT = 1.1926


def absolute_pairwise_difference(x):
    """Return the APD (Sn) scale estimate of ``x`` (NaN values are ignored)."""
    # MATLAB: I = ~isnan(x); x = x(I); x = x(:); x = sort(x);
    x = np.asarray(x, dtype=float).ravel()
    x = np.sort(x[~np.isnan(x)])

    # FIX: with fewer than two values the inner median is taken over an empty
    # set (MATLAB yields NaN with no explanation). Return NaN explicitly.
    if x.size < 2:
        return np.nan

    # FIX: MATLAB grew M inside the loop without preallocation; preallocate.
    m = np.empty(x.size)

    # MATLAB: for iElement = 1:length(x)
    for i in range(x.size):
        # MATLAB: y = [x(1:iElement-1);x(iElement+1:end)];   (all except x_i)
        y = np.delete(x, i)
        # MATLAB: y = abs(y-x(iElement)); M(iElement) = median(y);
        m[i] = np.median(np.abs(y - x[i]))

    # MATLAB: APD = 1.1926*median(M);
    return float(SN_CONSISTENCY_CONSTANT * np.median(m))
