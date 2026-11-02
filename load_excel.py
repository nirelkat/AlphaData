"""Replacement for the missing ``loadExcel.m`` script.

The original ``loadExcel`` was not supplied. The main script used it to create
a struct ``test`` holding one numeric column per parameter. This module returns
the equivalent pandas DataFrame, so ``test["clock"]`` in Python plays the role
of ``test.clock`` in MATLAB.

Expected sheet layout (as in ``reference_data.xlsx``):

    |        |  B     |  C   |  D   |  E    |  F    |  G   |
    |   3    | serial | p70  | p140 | clock | noise | sfdr |
    |   4... | 256    | -19.6| ...  |       |       |      |

* The table may start anywhere on the sheet (the reference starts at B3).
  The header row is found by looking for the ``serial`` cell.
* Columns are matched by header name (case-insensitive), not by position.
* Serial numbers are kept as text so leading zeros (e.g. ``020``) survive.
* Non-numeric parameter cells (blank, text, "N/A", ...) become NaN, which is
  what MATLAB's readtable produces and what the statistics functions are
  written to ignore ("omitnan").
"""

import pandas as pd

SERIAL_COLUMN = "serial"
# Parameter names in the order they appear in reference_data.xlsx.
PARAMETER_COLUMNS = ["p70", "p140", "clock", "noise", "sfdr"]


def load_excel(path, sheet_name=0):
    """Read the measurement sheet and return a DataFrame (MATLAB: ``test``)."""
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None, dtype=object)

    # Locate the header row/column: the cell whose text is "serial".
    is_serial = raw.map(lambda v: isinstance(v, str) and v.strip().lower() == SERIAL_COLUMN)
    hits = is_serial.stack()
    hits = hits[hits]
    if hits.empty:
        raise ValueError(f"No '{SERIAL_COLUMN}' header cell found in '{path}'.")
    header_row, first_col = hits.index[0]

    # Header names -> column positions, from the "serial" cell to the right.
    headers = {}
    for col in raw.columns[raw.columns.get_loc(first_col):]:
        name = raw.at[header_row, col]
        if isinstance(name, str) and name.strip():
            headers.setdefault(name.strip().lower(), col)

    missing = [name for name in PARAMETER_COLUMNS if name not in headers]
    if missing:
        raise ValueError(
            f"Missing parameter column(s) {missing} in '{path}'. "
            f"Expected headers: {[SERIAL_COLUMN] + PARAMETER_COLUMNS}."
        )

    body = raw.iloc[raw.index.get_loc(header_row) + 1:]
    test = pd.DataFrame({SERIAL_COLUMN: body[headers[SERIAL_COLUMN]]})
    for name in PARAMETER_COLUMNS:
        # Numeric parameters; anything unparsable becomes NaN (MATLAB behaviour).
        test[name] = pd.to_numeric(body[headers[name]], errors="coerce")

    # Drop completely empty rows (blank rows below the table).
    test = test.dropna(how="all").reset_index(drop=True)
    # Serial numbers as text: 256 -> "256", "020" stays "020".
    test[SERIAL_COLUMN] = test[SERIAL_COLUMN].map(
        lambda v: "" if pd.isna(v) else str(int(v)) if isinstance(v, float) and v.is_integer() else str(v)
    )
    return test
