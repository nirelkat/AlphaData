"""Port of the main MATLAB script.

Usage:
    python main.py path/to/measurements.xlsx [--sheet NAME]
    python main.py                 # only when USE_SYNTHETIC_CLOCK = True
"""

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from load_excel import load_excel
from statistical_data import statistical_data

# MATLAB: test.p1 = 70 + randn(size(test.p1)); % to be removed
# FIX: this debug line overwrote the real clock measurements with synthetic
# N(70, 1) noise, so every result was computed on fake data. It is removed;
# set this flag to True only to reproduce that test behaviour.
USE_SYNTHETIC_CLOCK = False

# Number of synthetic samples used when USE_SYNTHETIC_CLOCK is True and no
# Excel file is given (there is no file to take size(test.p1) from).
SYNTHETIC_SAMPLE_COUNT = 60


def print_results(name, average, median, wm, sigma, apd, h0, p_normal):
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


def main():
    parser = argparse.ArgumentParser(description="Statistical analysis of product parameters.")
    # Optional on the command line so synthetic mode can run without a file;
    # it is still required (checked below) when USE_SYNTHETIC_CLOCK is False.
    parser.add_argument("excel_file", nargs="?",
                        help="Excel file: serial number + 5 parameter columns")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first sheet)")
    args = parser.parse_args()

    # MATLAB: clear; close all; clc
    plt.close("all")

    # MATLAB: loadExcel
    if args.excel_file is not None:
        test = load_excel(args.excel_file, sheet_name=args.sheet)
    elif USE_SYNTHETIC_CLOCK:
        # No file given: build an empty table of SYNTHETIC_SAMPLE_COUNT rows;
        # p1 is filled with synthetic data below, p2-p5 stay NaN.
        print(f"No Excel file given - using {SYNTHETIC_SAMPLE_COUNT} synthetic clock samples.")
        test = pd.DataFrame(np.nan, index=range(SYNTHETIC_SAMPLE_COUNT),
                            columns=["p1", "p2", "p3", "p4", "p5"])
        test.insert(0, "serial", [f"SYN{i + 1:04d}" for i in range(SYNTHETIC_SAMPLE_COUNT)])
    else:
        parser.error("excel_file is required unless USE_SYNTHETIC_CLOCK = True")

    if USE_SYNTHETIC_CLOCK:
        # MATLAB: test.p1 = 70 + randn(size(test.p1));
        test["p1"] = 70 + np.random.randn(len(test))
        # test.loc[3, "p1"] = 77   # MATLAB: % test.p1(4) = 77;

    # MATLAB: clock = test.p1; p70 = test.p2;
    clock = test["p1"].to_numpy()
    p70 = test["p2"].to_numpy()

    # MATLAB: [average, Median, WM, sigma, APD] = statisticalData(clock, 'clock')
    print_results("clock", *statistical_data(clock, "clock"))

    # MATLAB: % [average, Median, WM, sigma, APD] = statisticalData(p70, 'p70')
    # print_results("p70", *statistical_data(p70, "p70"))

    plt.show()


if __name__ == "__main__":
    main()
