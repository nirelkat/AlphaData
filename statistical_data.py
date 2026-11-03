"""Statistics for one parameter (port and extension of statisticalData.m).

Two kinds of parameters are handled:

* continuous (clock, p70, p140, sfdr): mean, median, WM, sigma, APD, outliers
  (WM +/- 3*APD), shape (skewness, kurtosis) and the Kolmogorov-Smirnov
  normality test - the original MATLAB statistics plus shape measures.
* discrete (noise): integer-valued data with few distinct values. Mean, WM,
  APD and the KS test are not meaningful there, so the result holds the mode,
  its share, the frequency table and the off-mode share instead.

``is_discrete`` decides which one applies. Plotting lives in dashboards.py.
"""

import warnings
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from absolute_pairwise_difference import absolute_pairwise_difference
from weighted_mean import weighted_mean

OUTLIER_FACTOR = 3  # MATLAB: x > WM+3*APD | x < WM-3*APD
KS_ALPHA = 0.05  # MATLAB kstest default significance level

# A parameter is treated as discrete when every value is a whole number and it
# has at most this many distinct values (integer data with a wide spread is
# better described by the continuous statistics).
MAX_DISCRETE_LEVELS = 15


# --------------------------------------------------------------------------- #
# Detection
# --------------------------------------------------------------------------- #
def is_discrete(x):
    """True for integer-valued data with few distinct values (e.g. noise)."""
    valid = _valid(x)
    if valid.size == 0:
        return False
    whole = np.all(np.isclose(valid, np.round(valid)))
    return bool(whole and np.unique(valid).size <= MAX_DISCRETE_LEVELS)


# --------------------------------------------------------------------------- #
# Continuous parameters
# --------------------------------------------------------------------------- #
@dataclass
class ContinuousStats:
    name: str
    n: int  # valid (numeric) samples
    missing: int  # blank / text cells
    average: float
    median: float
    wm: float
    sigma: float
    apd: float
    scale: float  # APD, or sigma when APD == 0
    scale_name: str  # "APD" or "sigma"
    band_low: float  # WM - 3*scale
    band_high: float  # WM + 3*scale
    outliers: np.ndarray  # boolean mask over all rows (MATLAB variable I)
    skewness: float
    kurtosis: float  # excess kurtosis (0 for a normal distribution)
    ks_statistic: float  # D
    p_normal: float
    h0: float  # 1 = normality rejected, 0 = not rejected, NaN = not run
    kind: str = field(default="continuous", init=False)


def statistical_data(x, parameter_name):
    """Continuous statistics for one parameter.

    MATLAB: [average, Median, WM, sigma, APD, h0, p_normal] = statisticalData(x, parameterName)
    """
    x = np.asarray(x, dtype=float).ravel()
    valid = _valid(x)
    if valid.size == 0:
        # FIX: the MATLAB code had no guard and failed deep inside the
        # plotting / kstest calls for an all-NaN column.
        raise ValueError(f"Parameter '{parameter_name}' contains no numeric values.")

    # MATLAB: average = mean(x,"omitnan");
    average = float(np.mean(valid))
    # MATLAB: Median = median(x,"omitnan");
    median = float(np.median(valid))
    # MATLAB: WM = WeightedMean(x);
    wm = weighted_mean(valid)
    # MATLAB: sigma = std(x,"omitnan");   (MATLAB std uses N-1 -> ddof=1)
    sigma = float(np.std(valid, ddof=1)) if valid.size > 1 else np.nan
    # MATLAB: APD = AbsolutePairwiseDifference(x);
    apd = absolute_pairwise_difference(valid)

    # FIX: scale used for the outlier band, the KS test and the normal curves.
    # APD is 0 when more than half of the values are identical; the original
    # then had a zero-width outlier band and divided by zero in kstest.
    # In that case sigma is used instead of APD.
    if np.isfinite(apd) and apd > 0:
        scale, scale_name = apd, "APD"
    else:
        scale, scale_name = sigma, "sigma"
        warnings.warn(
            f"APD of '{parameter_name}' is {apd} (too many identical values); "
            f"using sigma = {sigma:.4g} for outliers and the normality test."
        )
    scale_ok = bool(np.isfinite(scale) and scale > 0)

    # MATLAB: I = (x > WM+3*APD) | (x < WM-3*APD);   (NaN compares False)
    band_low, band_high = wm - OUTLIER_FACTOR * scale, wm + OUTLIER_FACTOR * scale
    if scale_ok:
        with np.errstate(invalid="ignore"):
            outliers = (x > band_high) | (x < band_low)
    else:
        outliers = np.zeros(x.shape, dtype=bool)  # all values identical

    # Shape: skewness (asymmetry) and excess kurtosis (tail weight), bias-corrected.
    if valid.size >= 4 and np.ptp(valid) > 0:
        skewness = float(stats.skew(valid, bias=False))
        kurtosis = float(stats.kurtosis(valid, fisher=True, bias=False))
    else:
        skewness = kurtosis = np.nan

    # MATLAB: [h0, p_normal] = kstest((x - WM)/APD);
    # kstest ignores NaN and tests against N(0,1); h0 = 1 means "reject".
    # Note: WM and APD come from the same data, so the p-value is optimistic
    # (Lilliefors effect) - see README, "Kolmogorov-Smirnov test".
    if scale_ok:
        ks = stats.kstest((valid - wm) / scale, "norm")
        ks_statistic, p_normal = float(ks.statistic), float(ks.pvalue)
        h0 = float(p_normal < KS_ALPHA)
    else:
        ks_statistic = p_normal = h0 = np.nan  # no spread: test undefined

    return ContinuousStats(
        name=parameter_name, n=int(valid.size), missing=int(x.size - valid.size),
        average=average, median=median, wm=wm, sigma=sigma, apd=apd,
        scale=scale, scale_name=scale_name, band_low=band_low, band_high=band_high,
        outliers=outliers, skewness=skewness, kurtosis=kurtosis,
        ks_statistic=ks_statistic, p_normal=p_normal, h0=h0,
    )


# --------------------------------------------------------------------------- #
# Discrete parameters
# --------------------------------------------------------------------------- #
@dataclass
class DiscreteStats:
    name: str
    n: int
    missing: int
    values: np.ndarray  # distinct values, ascending
    counts: np.ndarray  # count of each value
    mode: float  # most frequent value
    mode_share: float  # fraction of samples equal to the mode
    off_mode_share: float  # fraction of samples different from the mode
    median: float
    sigma: float
    band: float  # outlier threshold: |x - mode| > band
    outliers: np.ndarray  # boolean mask over all rows
    rolling_window: int  # samples per window for the rolling mode share
    rolling_mode_share: np.ndarray  # per row, NaN until the window is full
    kind: str = field(default="discrete", init=False)


def discrete_data(x, parameter_name):
    """Discrete statistics for integer-valued data such as noise."""
    x = np.asarray(x, dtype=float).ravel()
    valid = _valid(x)
    if valid.size == 0:
        raise ValueError(f"Parameter '{parameter_name}' contains no numeric values.")

    values, counts = np.unique(valid, return_counts=True)
    # Mode: highest count; on a tie the value closest to the median wins.
    median = float(np.median(valid))
    top = values[counts == counts.max()]
    mode = float(top[np.argmin(np.abs(top - median))])
    mode_share = float(np.mean(valid == mode))
    sigma = float(np.std(valid, ddof=1)) if valid.size > 1 else 0.0

    # Outliers: more than 3 sigma from the mode, but never closer than one
    # step (1 unit): a neighbour of the mode is ordinary measurement jitter.
    band = max(OUTLIER_FACTOR * sigma, 1.0)
    with np.errstate(invalid="ignore"):
        outliers = np.abs(x - mode) > band

    # Rolling share of the mode over the sample order (trailing window).
    window = int(np.clip(round(valid.size / 10), 3, 20))
    is_mode = np.where(np.isnan(x), np.nan, (x == mode).astype(float))
    rolling = _rolling_mean(is_mode, window)

    return DiscreteStats(
        name=parameter_name, n=int(valid.size), missing=int(x.size - valid.size),
        values=values, counts=counts, mode=mode, mode_share=mode_share,
        off_mode_share=1.0 - mode_share, median=median, sigma=sigma, band=band,
        outliers=outliers, rolling_window=window, rolling_mode_share=rolling,
    )


def analyse(x, parameter_name):
    """Pick the discrete or continuous analysis automatically."""
    if is_discrete(x):
        return discrete_data(x, parameter_name)
    return statistical_data(x, parameter_name)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _valid(x):
    x = np.asarray(x, dtype=float).ravel()
    return x[~np.isnan(x)]


def _rolling_mean(values, window):
    """Trailing mean over ``window`` rows, ignoring NaN; NaN until the window fills."""
    out = np.full(values.shape, np.nan)
    for i in range(window - 1, values.size):
        chunk = values[i - window + 1:i + 1]
        chunk = chunk[~np.isnan(chunk)]
        if chunk.size:
            out[i] = chunk.mean()
    return out
