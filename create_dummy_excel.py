"""Generate a realistic sample Excel file for testing main.py.

Usage:
    python create_dummy_excel.py [output.xlsx] [--rows N] [--seed S]

Default output: sample_measurements.xlsx (60 rows, seed 42 - reproducible).

The layout copies reference_data.xlsx: the table starts at cell B3 with the
headers  serial | clock | p70 | p140 | noise | sfdr.

Distributions (p70, p140, noise, sfdr are modelled on the 6 rows of
reference_data.xlsx; clock follows the specified 11-15 operating range):

    parameter  ref. mean  ref. std  ref. range         generated as
    clock          -         -          -              normal(13.0, 0.9) kept in 11..15, 2 dp
    p70        -19.63     0.30      -20.01 .. -19.14   normal(-19.63, 0.30), 2 dp
    p140       -19.66     0.39      -20.23 .. -19.21   normal(-19.66, 0.39), 2 dp
    noise     -104.33     0.52      -105   .. -104     whole numbers, mostly -104
    sfdr        56.23     1.68       54.20 .. 58.20    normal(56.20, 1.60),  2 dp

Built-in edge cases:
  * Values are rounded to 2 decimal places (noise to whole numbers), like the
    real data, so identical neighbouring values occur (WeightedMean weight 200).
  * Blank cells in clock and p140 (read as NaN and ignored by the statistics).
  * A text entry ("N/A") in p70 (converted to NaN by load_excel).
  * An intentional outlier in clock (20.00, about 8 sigma above the mean).
  * Serial numbers are 3-digit text with leading zeros, like "020".
"""

import argparse

import numpy as np
import pandas as pd

DEFAULT_OUTPUT = "sample_measurements.xlsx"

# Same position as the table in reference_data.xlsx (cell B3; 0-based offsets).
START_ROW, START_COL = 2, 1

# clock: normal(mean, std) kept inside [low, high], rounded to 2 decimal places.
CLOCK_MEAN, CLOCK_STD = 13.0, 0.9
CLOCK_RANGE = (11.0, 15.0)

# Other continuous parameters: (mean, std), rounded to 2 decimal places.
NORMAL_SPECS = {
    "p70": (-19.63, 0.30),
    "p140": (-19.66, 0.39),
    "sfdr": (56.20, 1.60),
}

# noise: whole numbers with very low spread (reference: four -104, two -105).
NOISE_VALUES = [-105, -104, -103]
NOISE_PROBABILITIES = [0.30, 0.65, 0.05]

COLUMN_ORDER = ["serial", "clock", "p70", "p140", "noise", "sfdr"]

# Edge cases, as 0-based row positions.
OUTLIER_ROW, OUTLIER_COLUMN, OUTLIER_VALUE = 3, "clock", 20.00
BLANK_CELLS = [(10, "clock"), (25, "p140")]
TEXT_CELLS = [(12, "p70", "N/A")]


def generate_clock(rng, size):
    """Normal(CLOCK_MEAN, CLOCK_STD) values inside CLOCK_RANGE, 2 decimal places.

    Values falling outside the range (about 3% at std 0.9) are redrawn, so the
    shape stays normal while every value lies between 11 and 15.
    """
    low, high = CLOCK_RANGE
    values = rng.normal(CLOCK_MEAN, CLOCK_STD, size)
    outside = (values < low) | (values > high)
    while outside.any():
        values[outside] = rng.normal(CLOCK_MEAN, CLOCK_STD, outside.sum())
        outside = (values < low) | (values > high)
    return np.round(values, 2)


def create_dummy_data(rows=60, seed=42):
    """Return a DataFrame of synthetic measurements including the edge cases."""
    edge_rows = [OUTLIER_ROW] + [r for r, _ in BLANK_CELLS] + [r for r, _, _ in TEXT_CELLS]
    if rows <= max(edge_rows):
        raise ValueError(f"rows must be greater than {max(edge_rows)} to fit the edge cases.")
    if rows > 999:
        raise ValueError("rows must be at most 999 (3-digit serial numbers).")

    rng = np.random.default_rng(seed)
    data = {
        # Unique 3-digit serials as text, e.g. "020" (leading zeros kept).
        "serial": [f"{n:03d}" for n in rng.choice(np.arange(1, 1000), rows, replace=False)],
    }
    data["clock"] = generate_clock(rng, rows).astype(object)
    for name, (mean, std) in NORMAL_SPECS.items():
        # Columns are stored as object so text and blanks can be inserted.
        data[name] = np.round(rng.normal(mean, std, rows), 2).astype(object)
    data["noise"] = rng.choice(NOISE_VALUES, rows, p=NOISE_PROBABILITIES).astype(object)

    df = pd.DataFrame(data)[COLUMN_ORDER]
    df.loc[OUTLIER_ROW, OUTLIER_COLUMN] = OUTLIER_VALUE
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
    df.to_excel(args.output, index=False, startrow=START_ROW, startcol=START_COL)

    print(f"Wrote {len(df)} rows to {args.output} (table starts at cell B3)")
    print(f"  outlier : row {OUTLIER_ROW + 1} (serial {df.at[OUTLIER_ROW, 'serial']}) "
          f"{OUTLIER_COLUMN} = {OUTLIER_VALUE}")
    for row, col in BLANK_CELLS:
        print(f"  blank   : row {row + 1} (serial {df.at[row, 'serial']}) {col}")
    for row, col, text in TEXT_CELLS:
        print(f"  text    : row {row + 1} (serial {df.at[row, 'serial']}) {col} = '{text}'")


if __name__ == "__main__":
    main()
