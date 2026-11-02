"""Generate a realistic sample Excel file for testing main.py.

Usage:
    python create_dummy_excel.py [output.xlsx] [--rows N] [--seed S]

Default output: sample_measurements.xlsx (60 rows, seed 42 - reproducible).

Layout (what load_excel expects):
    | SN | p1 | p2 | p3 | p4 | p5 |

Built-in edge cases:
  * Every numeric value is rounded to 2 decimal places, like the real data,
    so some neighbouring values are identical (gap 0 -> WeightedMean weight 200).
  * Blank cells in p1 and p3 (read as NaN and ignored by the statistics).
  * A text entry ("N/A") in p2 (converted to NaN by load_excel).
  * An intentional outlier in p1 (77.00, about 7 sigma above the 70 mean).
"""

import argparse

import numpy as np
import pandas as pd

DEFAULT_OUTPUT = "sample_measurements.xlsx"

# Typical value (mean, std) for each parameter.
# p1 is the clock (~70, std 1), matching the MATLAB synthetic test data.
PARAMETER_SPECS = {
    "p1": (70.0, 1.0),
    "p2": (70.0, 0.5),
    "p3": (3.30, 0.05),
    "p4": (25.0, 2.0),
    "p5": (1.20, 0.10),
}

# Edge cases, as 0-based row positions.
OUTLIER_ROW, OUTLIER_VALUE = 3, 77.00  # MATLAB test case: test.p1(4) = 77
BLANK_CELLS = [(10, "p1"), (25, "p3")]
TEXT_CELLS = [(12, "p2", "N/A")]


def create_dummy_data(rows=60, seed=42):
    """Return a DataFrame of synthetic measurements including the edge cases."""
    edge_rows = [OUTLIER_ROW] + [r for r, _ in BLANK_CELLS] + [r for r, _, _ in TEXT_CELLS]
    if rows <= max(edge_rows):
        raise ValueError(f"rows must be greater than {max(edge_rows)} to fit the edge cases.")

    rng = np.random.default_rng(seed)
    data = {"SN": [f"SN{i + 1:04d}" for i in range(rows)]}
    for name, (mean, std) in PARAMETER_SPECS.items():
        # Round to 2 decimal places (0.01 resolution, like the real data).
        # Columns are stored as object so text and blanks can be inserted.
        data[name] = np.round(rng.normal(mean, std, rows), 2).astype(object)
    df = pd.DataFrame(data)

    df.loc[OUTLIER_ROW, "p1"] = OUTLIER_VALUE
    for row, col in BLANK_CELLS:
        df.loc[row, col] = None
    for row, col, text in TEXT_CELLS:
        df.loc[row, col] = text
    return df


def main():
    parser = argparse.ArgumentParser(description="Create a sample measurements Excel file.")
    parser.add_argument("output", nargs="?", default=DEFAULT_OUTPUT,
                        help=f"Output .xlsx path (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--rows", type=int, default=60, help="Number of rows (default: 60)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    args = parser.parse_args()

    df = create_dummy_data(args.rows, args.seed)
    df.to_excel(args.output, index=False)

    print(f"Wrote {len(df)} rows to {args.output}")
    print(f"  outlier : row {OUTLIER_ROW + 1} (SN{OUTLIER_ROW + 1:04d}) p1 = {OUTLIER_VALUE}")
    for row, col in BLANK_CELLS:
        print(f"  blank   : row {row + 1} (SN{row + 1:04d}) {col}")
    for row, col, text in TEXT_CELLS:
        print(f"  text    : row {row + 1} (SN{row + 1:04d}) {col} = '{text}'")


if __name__ == "__main__":
    main()
