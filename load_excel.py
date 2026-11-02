"""Replacement for the missing ``loadExcel.m`` script.

The original ``loadExcel`` was not supplied. From the way the main script uses
it, it must have created a struct called ``test`` with (at least) the numeric
fields ``test.p1`` ... ``test.p5`` - one column vector per parameter.

This module reproduces that contract: it reads an Excel sheet laid out as

    | serial number | param 1 | param 2 | param 3 | param 4 | param 5 |

and returns a pandas DataFrame with the columns ``serial, p1, p2, p3, p4, p5``
so that ``test["p1"]`` in Python plays the role of ``test.p1`` in MATLAB.

Assumptions (adjust if your original loadExcel differed):
  * The first row of the sheet is a header row.
  * Column 1 is the serial number; columns 2-6 are the five parameters.
  * Non-numeric parameter cells (blank, text, "N/A", ...) become NaN, which is
    what MATLAB's readtable/xlsread produce and what the statistics functions
    are written to ignore ("omitnan").
"""

import pandas as pd

PARAMETER_COLUMNS = ["p1", "p2", "p3", "p4", "p5"]


def load_excel(path, sheet_name=0):
    """Read the measurement sheet and return a DataFrame (MATLAB: ``test``)."""
    raw = pd.read_excel(path, sheet_name=sheet_name)

    if raw.shape[1] < 1 + len(PARAMETER_COLUMNS):
        raise ValueError(
            f"Expected at least {1 + len(PARAMETER_COLUMNS)} columns "
            f"(serial number + 5 parameters) in '{path}', found {raw.shape[1]}."
        )

    # Select columns by position so the header text in the sheet does not matter.
    test = raw.iloc[:, : 1 + len(PARAMETER_COLUMNS)].copy()
    test.columns = ["serial"] + PARAMETER_COLUMNS

    # Numeric parameters; anything unparsable becomes NaN (MATLAB behaviour).
    for col in PARAMETER_COLUMNS:
        test[col] = pd.to_numeric(test[col], errors="coerce")

    # Drop rows that are completely empty (trailing blank rows in Excel).
    test = test.dropna(how="all").reset_index(drop=True)
    return test
