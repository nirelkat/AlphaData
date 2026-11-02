# AlphaData – parameter distribution analysis (Python port of the MATLAB project)

Reads an Excel sheet of product measurements (serial number + 5 parameters),
computes classic and robust statistics for **every parameter** and plots each
parameter's distribution.

| MATLAB file                     | Python module                     |
|---------------------------------|-----------------------------------|
| main script                     | `main.py`                         |
| `loadExcel.m` (**missing**)     | `load_excel.py` (reconstructed)   |
| `statisticalData.m`             | `statistical_data.py`             |
| `WeightedMean.m`                | `weighted_mean.py`                |
| `AbsolutePairwiseDifference.m`  | `absolute_pairwise_difference.py` |
| –                               | `create_dummy_excel.py` (test data generator) |

## Parameters

Columns in table order:

| Column   | Typical values                    | Notes |
|----------|-----------------------------------|-------|
| `serial` | `256`, `201`, `020`, …            | Header may also be `SN`. Kept as text so leading zeros survive |
| `clock`  | 11 … 15 (mean ≈ 13.0, std ≈ 0.9)  | 2 decimal places |
| `p70`    | −20.0 … −19.1 (mean −19.63)       | 2 decimal places |
| `p140`   | −20.2 … −19.2 (mean −19.66)       | 2 decimal places |
| `noise`  | −105 … −104                       | Whole numbers, very low spread |
| `sfdr`   | 54.2 … 58.2 (mean 56.2)           | 2 decimal places |

`reference_data.xlsx` is a small sample of real measurements, kept in the
repository as a baseline reference. Its columns are in the order above. Its
`clock` values (3.2 … 7.6) predate the 11 … 15 range and were left unchanged.

## Input format

The layout follows `reference_data.xlsx`: a header row containing `serial`, `clock`,
`p70`, `p140`, `noise`, `sfdr`, followed by one row per product.

- **Table position:** the table may start anywhere on the sheet (the reference
  starts at cell B3). The loader finds it by the `serial` (or `SN`) header cell.
- **Columns:** matched by header name (case-insensitive), so their order does not
  matter.
- **Bad cells:** blank or text cells in parameter columns become NaN and are
  ignored.

## Install & run

```bash
pip install -r requirements.txt
```

```bash
python main.py path/to/measurements.xlsx
```

Optional `--sheet NAME` selects a worksheet (default: the first).

### Viewing the results

All five parameters are analysed in one run, in the order `clock`, `p70`, `p140`,
`noise`, `sfdr`.

**Console:** one block per parameter, then a summary table:

```
--- clock ---
average  = 12.9210
Median   = 12.8200
WM       = 12.7701
sigma    = 1.1537
APD      = 0.8348
h0       = 0   (1 = normality rejected at alpha = 0.05)
p_normal = 0.5021
outliers = 1  (serials: 361)

=== Summary ===
parameter       mean    median        WM    sigma      APD   h0  p_normal  outliers
clock         12.921    12.820    12.770    1.154    0.835    0     0.502         1
...
```

**Figures:** three windows per parameter (**15 in total**). Each window title
names the parameter and the plot:
- `<parameter> - data vs. sample`: measurements by sample number, outliers in
  red, with the mean and WM lines;
- `<parameter> - histogram`: bin width 0.5;
- `<parameter> - CDF`: empirical CDF against a normal CDF centred on WM.

All windows open together when the analysis finishes. Closing them all ends the
program.

**Outliers** are values more than 3 × APD away from WM. They are listed by serial
number in the console and shown in red in the first plot.

## Weighted Mean (WM)

WM sorts the values and averages the midpoints of neighbouring pairs, weighting
each midpoint by `1 / gap`. A gap of 0 (identical values) would give an infinite
weight, so those weights are set to **200**, matching the original MATLAB code.

This is intentional and relies on the data's precision: all measurements are
rounded to **2 decimal places** (0.01 resolution). Any non-zero gap is therefore
at least 0.01, giving a weight of at most 100, so identical values (200) always
carry the highest weight. If the data are ever stored with finer precision, gaps
below 0.005 would get weights above 200 and this value should be revisited.

## `noise` and APD = 0

`noise` is measured in whole numbers and most readings are identical (e.g. −104).
More than half of the pairwise differences are then 0, so **APD = 0**. With the
original MATLAB logic the outlier band WM ± 3·APD would have zero width and every
reading would be flagged as an outlier.

When APD is 0, the program uses **sigma** (standard deviation) instead for:
- the outlier band;
- the normality test;
- the normal curve in the CDF plot.

A warning is printed when this happens, and APD itself is still reported as 0.

The normality test usually rejects normality (`h0 = 1`) for `noise`. This is
expected: whole-number data forms a staircase that cannot match a smooth normal
curve.

## Sample data for testing

`create_dummy_excel.py` generates a reproducible test file, `sample_measurements.xlsx`,
with the same layout as `reference_data.xlsx` (table at B3, columns `serial`,
`clock`, `p70`, `p140`, `noise`, `sfdr`). It has 60 rows. The distributions are:
- **`clock`:** normal with mean 13.0 and std 0.9, kept between 11 and 15 (values
  outside are redrawn), rounded to 2 decimal places;
- **`p70`, `p140`, `sfdr`:** normal distributions modelled on the reference data,
  rounded to 2 decimal places;
- **`noise`:** whole numbers, mostly −104, some −105, and occasionally −103.

It also includes these edge cases:
- an outlier in `clock` (row 4, value 20.00, outside the 11–15 range);
- blank cells in `clock` and `p140`;
- a text entry (`N/A`) in `p70`;
- serials with leading zeros (e.g. `020`).

```bash
python create_dummy_excel.py
```

```bash
python main.py sample_measurements.xlsx
```

Options: `python create_dummy_excel.py my_file.xlsx --rows 100 --seed 7`.

## Synthetic mode (no Excel file)

Setting `USE_SYNTHETIC_CLOCK = True` in `main.py` replaces `clock` with random data,
like the original MATLAB test line. The original MATLAB line used N(70, 1); this
mode uses the same `clock` generator as `create_dummy_excel.py`: mean 13.0, std
0.9, kept between 11 and 15, rounded to 2 decimal places.

In this mode the Excel file is optional:
- **No file:** `python main.py` runs on 60 generated samples for all five
  parameters.
- **File given:** the file is loaded and only its `clock` column is replaced.
