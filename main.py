"""Port of the main MATLAB script.

Usage:
    python main.py path/to/measurements.xlsx [--sheet NAME]
"""

import argparse

import matplotlib.pyplot as plt

from load_excel import load_excel
from statistical_data import statistical_data

# MATLAB: test.p1 = 70 + randn(size(test.p1)); % to be removed
# FIX: this debug line overwrote the real clock measurements with synthetic
# N(70, 1) noise, so every result was computed on fake data. It is removed;
# set this flag to True only to reproduce that test behaviour.
USE_SYNTHETIC_CLOCK = False


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
    parser.add_argument("excel_file", help="Excel file: serial number + 5 parameter columns")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first sheet)")
    args = parser.parse_args()

    # MATLAB: clear; close all; clc
    plt.close("all")

    # MATLAB: loadExcel
    test = load_excel(args.excel_file, sheet_name=args.sheet)

    if USE_SYNTHETIC_CLOCK:
        import numpy as np
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
