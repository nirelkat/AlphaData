# AlphaData – parameter distribution analysis (Python port of the MATLAB project)

Reads an Excel sheet (serial number + 5 numeric parameter columns), computes
classic and robust statistics for a parameter and plots its distribution.

| MATLAB file                     | Python module                     |
|---------------------------------|-----------------------------------|
| main script                     | `main.py`                         |
| `loadExcel.m` (**missing**)     | `load_excel.py` (reconstructed)   |
| `statisticalData.m`             | `statistical_data.py`             |
| `WeightedMean.m`                | `weighted_mean.py`                |
| `AbsolutePairwiseDifference.m`  | `absolute_pairwise_difference.py` |

## Input format

First row = headers (any text). Column A = serial number, columns B–F = parameters
p1…p5. Blank or text cells in parameter columns are treated as NaN and ignored.

## Weighted Mean (WM)

WM sorts the values and averages the midpoints of neighbouring pairs, weighting
each midpoint by `1 / gap`. A gap of 0 (identical values) would give an infinite
weight, so those weights are set to **200**, matching the original MATLAB code.

This is intentional and relies on the data's precision: all measurements are
rounded to **2 decimal places** (0.01 resolution). Any non-zero gap is therefore
at least 0.01, giving a weight of at most 100, so identical values (200) always
carry the highest weight. If the data are ever stored with finer precision, gaps
below 0.005 would get weights above 200 and this value should be revisited.

## Install & run

```bash
pip install -r requirements.txt
```

```bash
python main.py path/to/measurements.xlsx
```

Optional `--sheet NAME` selects a worksheet (default: the first). The statistics are
printed to the console and three figures open (scatter with outliers, histogram,
empirical vs. normal CDF).

### Sample data for testing

`create_dummy_excel.py` generates a reproducible test file, `sample_measurements.xlsx`.
It has 60 rows with columns `SN`, `p1`–`p5`, all values rounded to 2 decimal places. It
also includes these edge cases:
- an outlier in `p1` (row 4, value 77.00);
- blank cells in `p1` and `p3`;
- a text entry (`N/A`) in `p2`.

```bash
python create_dummy_excel.py
```

```bash
python main.py sample_measurements.xlsx
```

Options: `python create_dummy_excel.py my_file.xlsx --rows 100 --seed 7`.

### Synthetic mode (no Excel file)

Setting `USE_SYNTHETIC_CLOCK = True` in `main.py` replaces `p1` with random
N(70, 1) data, like the original MATLAB test line. In this mode the Excel file is
optional: `python main.py` alone runs on 60 synthetic samples. If a file is given,
it is loaded and only its `p1` column is replaced.

To analyse `p2` (`p70`) as well, uncomment the corresponding line in `main.py`,
as in the original script.
