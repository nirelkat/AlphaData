"""Port of the main MATLAB script.

Runs the statistical analysis (statisticalData) for all five parameters
(clock, p70, p140, noise, sfdr) and opens three figures per parameter.

Usage:
    python main.py path/to/measurements.xlsx [--sheet NAME]
    python main.py                 # only when USE_SYNTHETIC_CLOCK = True
"""

import argparse
import io

import matplotlib.pyplot as plt
import numpy as np

from create_dummy_excel import create_dummy_data, generate_clock
from load_excel import PARAMETER_COLUMNS, SERIAL_COLUMN, load_excel
from statistical_data import statistical_data

# MATLAB: test.p1 = 70 + randn(size(test.p1)); % to be removed
# FIX: this debug line overwrote the real clock measurements with synthetic
# noise, so every result was computed on fake data. It is removed; set this
# flag to True only to reproduce that test behaviour.
# The original used N(70, 1); the synthetic clock now uses the realistic spec
# from create_dummy_excel.py: normal(13.0, 0.9) within 11-15, 2 decimal places.
USE_SYNTHETIC_CLOCK = False

# Number of synthetic samples used when USE_SYNTHETIC_CLOCK is True and no
# Excel file is given (all five columns are then generated).
SYNTHETIC_SAMPLE_COUNT = 60


def print_results(name, serials, average, median, wm, sigma, apd, h0, p_normal, outliers):
    """MATLAB displayed the outputs because the call had no semicolon."""
    print(f"--- {name} ---")
    print(f"average  = {average:.4f}")
    print(f"Median   = {median:.4f}")
    print(f"WM       = {wm:.4f}")
    print(f"sigma    = {sigma:.4f}")
    print(f"APD      = {apd:.4f}")
    # FIX: the original requested only 5 of the 7 outputs, so the normality
    # test result was computed but never shown.
    print(f"h0       = {h0}   (1 = normality rejected at alpha = 0.05)")
    print(f"p_normal = {p_normal:.4g}")
    flagged = ", ".join(serials[outliers]) if outliers.any() else "none"
    print(f"outliers = {int(outliers.sum())}  (serials: {flagged})")
    print()


def print_summary(results):
    """One table with the key numbers of every parameter."""
    print("=== Summary ===")
    print(f"{'parameter':<10}{'mean':>10}{'median':>10}{'WM':>10}{'sigma':>9}"
          f"{'APD':>9}{'h0':>5}{'p_normal':>10}{'outliers':>10}")
    for name, (average, median, wm, sigma, apd, h0, p_normal, outliers) in results.items():
        print(f"{name:<10}{average:>10.3f}{median:>10.3f}{wm:>10.3f}{sigma:>9.3f}"
              f"{apd:>9.3f}{h0!s:>5}{p_normal:>10.3g}{int(outliers.sum()):>10}")


def load_synthetic_table():
    """All five columns from the dummy generator, read through load_excel."""
    buffer = io.BytesIO()
    create_dummy_data(SYNTHETIC_SAMPLE_COUNT).to_excel(buffer, index=False)
    buffer.seek(0)
    return load_excel(buffer)


def main():
    parser = argparse.ArgumentParser(description="Statistical analysis of product parameters.")
    # Optional on the command line so synthetic mode can run without a file;
    # it is still required (checked below) when USE_SYNTHETIC_CLOCK is False.
    parser.add_argument("excel_file", nargs="?",
                        help="Excel file with columns serial, clock, p70, p140, noise, sfdr")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first sheet)")
    args = parser.parse_args()

    # MATLAB: clear; close all; clc
    plt.close("all")

    # MATLAB: loadExcel
    if args.excel_file is not None:
        test = load_excel(args.excel_file, sheet_name=args.sheet)
    elif USE_SYNTHETIC_CLOCK:
        print(f"No Excel file given - using {SYNTHETIC_SAMPLE_COUNT} synthetic samples.\n")
        test = load_synthetic_table()
    else:
        parser.error("excel_file is required unless USE_SYNTHETIC_CLOCK = True")

    if USE_SYNTHETIC_CLOCK:
        # MATLAB: test.p1 = 70 + randn(size(test.p1));   (p1 was named "clock")
        test["clock"] = generate_clock(np.random.default_rng(), len(test))
        # MATLAB: % test.p1(4) = 77;   ->   test.loc[3, "clock"] = 20

    serials = test[SERIAL_COLUMN].to_numpy(dtype=str)

    # MATLAB: [average, Median, WM, sigma, APD] = statisticalData(clock, 'clock')
    # MATLAB: % [average, Median, WM, sigma, APD] = statisticalData(p70, 'p70')
    # The original analysed clock (and optionally p70) one call at a time;
    # the same call is now made for every parameter.
    results = {}
    for name in PARAMETER_COLUMNS:
        try:
            results[name] = statistical_data(test[name].to_numpy(), name)
        except ValueError as err:  # e.g. a column with no numeric values
            print(f"--- {name} --- skipped: {err}\n")
            continue
        print_results(name, serials, *results[name])

    if results:
        print_summary(results)

    # 3 figures per parameter (up to 15 windows); all stay open until closed.
    plt.show()


if __name__ == "__main__":
    main()
