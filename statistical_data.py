"""Port of statisticalData.m.

Computes classic and robust statistics for one parameter, runs a
Kolmogorov-Smirnov normality test and draws the three original figures:
  1. data vs. sample index, with outliers in red and the mean / WM lines
  2. histogram (bin width 0.5)
  3. empirical CDF vs. a normal CDF centred on WM with scale APD
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from absolute_pairwise_difference import absolute_pairwise_difference
from weighted_mean import weighted_mean

HISTOGRAM_BIN_WIDTH = 0.5  # MATLAB: histogram(x, 'BinWidth',0.5)
OUTLIER_FACTOR = 3  # MATLAB: x > WM+3*APD | x < WM-3*APD


def statistical_data(x, parameter_name):
    """Python equivalent of
    ``[average, Median, WM, sigma, APD, h0, p_normal] = statisticalData(x, parameterName)``
    """
    x = np.asarray(x, dtype=float).ravel()
    valid = x[~np.isnan(x)]

    if valid.size == 0:
        # FIX: the MATLAB code had no guard and failed deep inside the
        # plotting / kstest calls for an all-NaN column.
        raise ValueError(f"Parameter '{parameter_name}' contains no numeric values.")

    # ---- Statistics --------------------------------------------------------
    # MATLAB: average = mean(x,"omitnan");
    average = float(np.nanmean(x))
    # MATLAB: Median = median(x,"omitnan");
    median = float(np.nanmedian(x))
    # MATLAB: WM = WeightedMean(x);
    wm = weighted_mean(x)
    # MATLAB: sigma = std(x,"omitnan");   (MATLAB std uses N-1 -> ddof=1)
    sigma = float(np.nanstd(x, ddof=1)) if valid.size > 1 else np.nan
    # MATLAB: APD = AbsolutePairwiseDifference(x);
    apd = absolute_pairwise_difference(x)

    # MATLAB: I = (x > WM+3*APD) | (x < WM-3*APD);
    # (NaN comparisons are False, as in MATLAB.)
    with np.errstate(invalid="ignore"):
        outliers = (x > wm + OUTLIER_FACTOR * apd) | (x < wm - OUTLIER_FACTOR * apd)

    # MATLAB: range = 1:length(x);
    # (renamed: "range" shadowed a MATLAB built-in; MATLAB indices are 1-based)
    sample_index = np.arange(1, x.size + 1)

    # ---- Figure 1: data vs. sample index ------------------------------------
    # MATLAB: figure; hold on
    fig1, ax1 = plt.subplots()
    # MATLAB: plot(x, '.b', 'MarkerSize', 15)
    ax1.plot(sample_index, x, ".b", markersize=15, label="data")
    # MATLAB: plot(range(I), x(I), '.r', 'MarkerSize', 15)
    ax1.plot(sample_index[outliers], x[outliers], ".r", markersize=15, label="outliers")
    # MATLAB: plot(1:length(x), average*ones(size(x)), '--')
    ax1.plot(sample_index, np.full(x.shape, average), "--", label="mean")
    # MATLAB: plot(1:length(x), WM*ones(size(x)), '--')
    ax1.plot(sample_index, np.full(x.shape, wm), "--", label="WM")
    # MATLAB: legend('data', 'mean', 'WM')
    # FIX: four lines were plotted but only three legend entries given, so the
    # red outlier markers were labelled "mean" and the mean line "WM", while
    # the WM line had no label. An explicit "outliers" entry is added.
    ax1.legend()
    # MATLAB: title([parameterName, ' average = ', num2str(round(average,2)), ...])
    ax1.set_title(
        f"{parameter_name} average = {_num2str(average)}, "
        f"{parameter_name} WM = {_num2str(wm)}"
    )

    # ---- Figure 2: histogram ------------------------------------------------
    # MATLAB: figure; histogram(x, 'BinWidth',0.5); title(parameterName)
    fig2, ax2 = plt.subplots()
    ax2.hist(valid, bins=_bin_edges(valid, HISTOGRAM_BIN_WIDTH), edgecolor="black")
    ax2.set_title(parameter_name)

    # ---- Normality test -----------------------------------------------------
    # MATLAB: [h0, p_normal] = kstest((x - WM)/APD);
    # MATLAB kstest ignores NaN and tests against N(0,1) at alpha = 0.05;
    # h0 = 1 means "reject normality".
    # Note: WM and APD are estimated from the same data, so the p-value is
    # optimistic (Lilliefors effect). This matches the original behaviour.
    scale_ok = np.isfinite(apd) and apd > 0
    if scale_ok:
        p_normal = float(stats.kstest((valid - wm) / apd, "norm").pvalue)
        h0 = int(p_normal < 0.05)
    else:
        # FIX: if APD == 0 (e.g. more than half the values identical) the
        # original divided by zero and kstest received Inf/NaN.
        warnings.warn(
            f"APD of '{parameter_name}' is {apd}; skipping the KS normality test."
        )
        h0, p_normal = np.nan, np.nan

    # ---- Figure 3: empirical CDF vs. normal CDF ------------------------------
    # MATLAB: figure; cdfplot(x); hold on
    fig3, ax3 = plt.subplots()
    sorted_x = np.sort(valid)
    ecdf_y = np.arange(1, sorted_x.size + 1) / sorted_x.size
    # Prepend (min, 0) so the staircase rises from 0 like MATLAB's cdfplot.
    ax3.step(np.r_[sorted_x[0], sorted_x], np.r_[0.0, ecdf_y], where="post",
             label="Empirical CDF")
    ax3.grid(True)  # cdfplot turns the grid on
    if scale_ok:
        # MATLAB: x_values = linspace(min(x),max(x));   (100 points by default)
        x_values = np.linspace(sorted_x[0], sorted_x[-1], 100)
        # MATLAB: plot(x_values,normcdf((x_values-WM)/APD,0,1),'r-')
        # FIX (label only): the curve is the normal CDF with mean WM and
        # std APD, i.e. the standard normal applied to standardised data;
        # the label now says so instead of "Standard Normal CDF".
        ax3.plot(x_values, stats.norm.cdf((x_values - wm) / apd, 0, 1), "r-",
                 label="Normal CDF (mean = WM, std = APD)")
    # MATLAB: legend(...,'Location','best'); title(parameterName)
    ax3.legend(loc="best")
    ax3.set_title(parameter_name)
    ax3.set_xlabel("x")
    ax3.set_ylabel("F(x)")

    return average, median, wm, sigma, apd, h0, p_normal


def _num2str(value):
    """Mimic MATLAB num2str(round(value, 2)) - no trailing zeros."""
    return f"{round(value, 2):g}"


def _bin_edges(values, width):
    """Bin edges aligned to multiples of ``width`` (like MATLAB 'BinWidth')."""
    lo = np.floor(values.min() / width) * width
    hi = np.ceil(values.max() / width) * width
    if hi <= lo:
        hi = lo + width
    return np.arange(lo, hi + width / 2, width)
