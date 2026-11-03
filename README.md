# AlphaData – parameter distribution analysis

Reads an Excel sheet of product measurements (serial number + 5 parameters),
analyses the distribution of every parameter and presents the results as
dashboards: **one page per parameter** plus an **executive summary**. Each page
can be saved as PNG or PDF.

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python create_dummy_excel.py
```

```bash
python main.py sample_measurements.xlsx
```

The first command installs the dependencies. The second creates a 60-row test
file. The third opens the dashboard window and prints the statistics to the
console.

### Command-line options

| Option | Meaning |
|---|---|
| `excel_file` | The measurement workbook (required) |
| `--sheet NAME` | Worksheet name or index (default: the first sheet) |
| `--export DIR` | Save every page to `DIR` without clicking anything |
| `--format pdf\|png\|both` | Format for `--export` (default `pdf`). PDF export also writes `<name>_report.pdf` with all pages in one file |
| `--no-show` | Don't open the window (for batch export) |

Example: export a full PDF report without opening the window.

```bash
python main.py reference_data.xlsx --export reports --no-show
```

## Input format

The layout follows `reference_data.xlsx`: a header row with `serial`, `clock`,
`p70`, `p140`, `noise`, `sfdr`, then one row per product.

- **Table position:** the table may start anywhere on the sheet (the reference
  starts at cell B3). The loader finds it by the `serial` (or `SN`) header cell.
- **Columns:** matched by header name (case-insensitive), so their order doesn't
  matter.
- **Bad cells:** blank or text cells (e.g. `N/A`) in parameter columns are treated
  as missing and ignored.
- **Serial numbers:** kept as text, so leading zeros (`020`) survive.

## Parameters

| Column   | Typical values                    | Type | Notes |
|----------|-----------------------------------|------|-------|
| `serial` | `256`, `201`, `020`, …            | –    | Header may also be `SN` |
| `clock`  | 11 … 15 (mean ≈ 13)               | continuous | 2 decimal places |
| `p70`    | −20.0 … −19.1 (mean −19.63)       | continuous | 2 decimal places |
| `p140`   | −20.2 … −19.2 (mean −19.66)       | continuous | 2 decimal places |
| `noise`  | −105 … −104                       | discrete   | Whole numbers, very low spread |
| `sfdr`   | 54.2 … 58.2 (mean 56.2)           | continuous | 2 decimal places |

`reference_data.xlsx` is a small sample of real measurements, kept in the
repository as a baseline reference.

The type is **detected automatically**, not hard-coded (see
[Discrete parameters](#discrete-parameters)).

## Dashboards

### One window, six pages

All results open in **a single window** that shows one page at a time. A
navigation bar along the bottom switches pages:

```
[<]  [clock] [p70] [p140] [sfdr] [noise] [Summary]  [>]     [Save PNG] [Save PDF]
```

| Control | Action |
|---|---|
| Page buttons | Jump straight to that page; the current page is highlighted in blue |
| `<` / `>` | Previous / next page (wraps around at either end) |
| ← / → or Page Up / Page Down | Previous / next page |
| Home / End | First / last page |
| `1` … `6` | Jump to page 1 … 6 |
| **Save PNG** / **Save PDF** | Save the page currently shown (see [Saving pages](#saving-pages)) |

Page order:
1. Continuous parameters, in sheet order: `clock`, `p70`, `p140`, `sfdr`.
2. Discrete parameters: `noise`.
3. Executive summary.

The display order doesn't change the dataset's column order. The window title
and the page footer show the current page (e.g. `page 2/6`).

### Continuous parameter page

A 2 × 2 grid of plots with a statistics panel on the right:

| Plot | What it shows |
|---|---|
| **Data vs. sample** | Every measurement in row order. Shows the mean and WM lines, the shaded outlier band WM ± 3·APD, and outliers in red labelled with their serial number |
| **Histogram** | Automatic bin width (see [Histogram bins](#histogram-bins-and-density-curves)), a smoothed density curve (KDE) and the normal curve N(WM, APD) |
| **Empirical CDF vs. normal** | The data's cumulative distribution against the normal CDF used in the KS test. The title shows the KS statistic D and p-value |
| **Normal Q-Q plot** | Ordered data against normal quantiles, with a reference line WM + APD·z. Points on the line mean normal-looking data |

The **statistics panel** lists:
- **sample:** valid and missing counts;
- **location:** mean, median, WM;
- **spread:** σ, APD, min/max;
- **shape:** skewness, excess kurtosis;
- **outliers:** the band, count and serials;
- **normality:** D, `p_normal` and `h0`.

### Discrete parameter page

Used for integer-valued data such as `noise`:

| Plot | What it shows |
|---|---|
| **Data vs. sample** | Measurements with whole-number y-ticks and the mode line. Side bars show how many samples sit at each value. A strip below tracks the **rolling share of the mode** over the sample order, which reveals drift (e.g. readings moving from −104 to −105) |
| **Value counts** | One bar per value, labelled `value: count (percent)`, e.g. `−104: 45 (75%)`. The mode is orange; outlier values are red |
| **Cumulative distribution** | Percentage of samples at or below each value |
| **Frequency distribution** | Table of value, count, share and cumulative share. The mode row and outlier rows are highlighted |

The **statistics panel** lists:
- the mode and its share;
- the off-mode share;
- the number of distinct values;
- the median, min/max and σ;
- outliers.

Mean, WM and APD aren't shown, and the KS test isn't run (see below).

### Executive summary page

| Element | What it shows |
|---|---|
| **Continuous parameters table** | n, mean, median, WM, σ, APD, skewness, KS p-value, normal yes/no, outlier count |
| **Discrete parameters table** | n, mode, mode share, off-mode share, distinct values, outlier count |
| **Correlation heatmap** | Spearman rank correlation between all 5 parameters (blue = negative, red = positive) |
| **Overview box plot** | All parameters on one scale as robust z-scores, so their spreads and outliers can be compared. Dotted lines at ±3 mark the outlier threshold of the continuous parameters |

### Saving pages

- **From the window:** **Save PNG** / **Save PDF** save the page currently shown.
  - Files go to `<excel name>_dashboards/` next to the Excel file, or to the
    `--export` folder if one was given.
  - Names follow the page, e.g. `sample_measurements_05_noise.png`.
  - The navigation bar isn't included in the saved file. A confirmation appears
    in the window's top-right corner.
- **All pages at once, without the window:** use `--export DIR` (see the
  [command-line options](#command-line-options)).
- **Manual:** the standard matplotlib toolbar save icon also works, but it saves
  the window as shown, navigation bar included.

## Statistics reference

Notation: x₁, …, xₙ are the valid (numeric) values of one parameter;
x(1) ≤ x(2) ≤ … ≤ x(n) are the same values sorted.

### Mean, median, standard deviation

```math
\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i
\qquad\qquad
\sigma = \sqrt{\frac{1}{n-1}\sum_{i=1}^{n} \left(x_i - \bar{x}\right)^2}
```

The median is the middle sorted value (the average of the two middle values when
n is even). The mean and σ react strongly to outliers; the median, WM and APD
don't.

### Weighted Mean (WM)

WM is a robust centre that gives the most weight to where the data is
**densest**. It walks through the sorted values and looks at each neighbouring
pair x(i), x(i+1), for i = 1 … n−1:

| Symbol | Formula | Meaning |
|---|---|---|
| mᵢ | (x(i) + x(i+1)) / 2 | Midpoint of the pair |
| gᵢ | x(i+1) − x(i) | Gap between the pair (never negative, the values are sorted) |
| wᵢ | 1 / gᵢ, or **200** when gᵢ = 0 | Weight of the midpoint |
| WM | Σ wᵢ·mᵢ / Σ wᵢ | Weighted average of the midpoints |

The same in mathematical notation:

```math
m_i = \frac{x_{(i)} + x_{(i+1)}}{2}
```

```math
g_i = x_{(i+1)} - x_{(i)}
```

```math
w_i =
\begin{cases}
  \dfrac{1}{g_i} & \text{if } g_i > 0 \\[6pt]
  200            & \text{if } g_i = 0 \;\text{(identical values)}
\end{cases}
```

```math
\mathrm{WM} = \frac{\sum_{i=1}^{n-1} w_i \, m_i}{\sum_{i=1}^{n-1} w_i}
```

- **Close pairs dominate.** Tightly packed values (small gaps) carry large weights;
  an isolated outlier sits next to a large gap and barely counts.
- **Identical values get weight 200.** A gap of 0 would give an infinite weight.
  Only those weights are replaced; no other weight is capped. This matches the
  original MATLAB code (`weights(weights == Inf) = 200`).
- **Why 200 is safe:** all measurements are rounded to **2 decimal places**, so
  every non-zero gap is at least 0.01 and its weight at most 1 / 0.01 = 100.
  Identical values (200) therefore always carry the highest weight. If the data
  ever has finer precision, gaps below 0.005 would get weights above 200 and this
  value should be revisited.
- **Small samples:** WM can be pulled toward a single close pair. In the 6-row
  reference file, 14.9 and 15.01 sit close together, which puts `clock`'s WM
  (14.48) well above its mean (13.84).

### APD – Absolute Pairwise Difference (Rousseeuw–Croux Sₙ)

APD is a robust measure of spread: an outlier-resistant replacement for σ.

```math
\mathrm{APD} = S_n = c \cdot \operatorname{med}_{i} \left( \operatorname{med}_{j \ne i} \left| x_i - x_j \right| \right),
\qquad c = 1.1926
```

1. For each value xᵢ, take the **median distance** to all other values. This is
   the typical distance from that point to the rest of the data.
2. Take the **median of those medians**.
3. Multiply by c = 1.1926. This constant makes Sₙ equal to σ on average when the
   data is normal, so APD and σ can be compared directly.

Properties:
- **Breakdown point of 50%:** almost half the data can be replaced by arbitrary
  values before APD is ruined. A single outlier would ruin σ.
- **Unlike the MAD** (median absolute deviation), Sₙ doesn't assume the data is
  symmetric around a centre.

Reference: Rousseeuw & Croux (1993), *Alternatives to the Median Absolute
Deviation*, JASA 88(424). This code uses the ordinary median for both steps and
excludes j = i. The paper's low/high-median variant gives nearly identical values.

#### When APD is 0 (console warning)

If more than half of the values are identical, most pairwise distances are 0,
so both medians are 0 and **APD = 0**. An outlier band of WM ± 3·0 would have zero
width: every value different from WM would be flagged. The KS test would also
divide by zero.

The program then:
- prints a warning: `UserWarning: APD of '<name>' is 0.0 (too many identical
  values); using sigma = … for outliers and the normality test`. Many terminals
  and IDEs show warnings in red;
- uses **σ instead of APD** for the outlier band, the KS test and the normal
  curves. The page labels change accordingly, e.g. "Outliers (WM ± 3·sigma)";
- still reports APD itself as 0.

This only applies to **continuous** parameters. Integer data such as `noise` is
detected as discrete and never uses APD, so it doesn't produce this warning.

### Outliers

- **Continuous:** a value is an outlier when it lies outside WM ± 3·APD. For
  normal data that band covers about 99.7% of values.
- **Discrete:** a value is an outlier when |x − mode| > max(3σ, 1). The minimum of
  1 means a neighbour of the mode (e.g. −105 when the mode is −104) is never
  flagged, because one step is ordinary measurement jitter.

Outliers are listed by serial number on each page and in the console.

### Skewness and excess kurtosis

Both use the bias-corrected sample formulas (SciPy `skew` / `kurtosis` with
`bias=False`):

- **Skewness:** 0 for symmetric data. Positive means a longer right tail; negative
  means a longer left tail.
- **Excess kurtosis:** 0 for a normal distribution. Positive means heavier tails
  (more extreme values); negative means lighter tails, e.g. flat or two-peaked
  data.

Both are **sensitive to outliers**. In the sample file, the single `clock` value of
20.00 raises its skewness to about 4. Read them together with the Q-Q plot.

### Kolmogorov–Smirnov test: `h0` and `p_normal`

The test answers one question: *could these values plausibly come from a normal
distribution?*

**Setup.** Each value is standardised with the robust centre and spread,
zᵢ = (xᵢ − WM) / APD. The zᵢ are then compared with the standard normal
distribution Φ:

- H₀ (null hypothesis): the data comes from a normal distribution with mean WM and
  standard deviation APD;
- H₁: it doesn't.

**Test statistic.** The empirical CDF Fₙ(z) is the fraction of samples ≤ z. The
KS statistic Dₙ is the **largest vertical gap** between Fₙ and Φ:

```math
D_n = \sup_{z} \left| F_n(z) - \Phi(z) \right|
    = \max_{i} \max\left( \frac{i}{n} - \Phi\left(z_{(i)}\right),\; \Phi\left(z_{(i)}\right) - \frac{i-1}{n} \right)
```

This is the gap visible in the *Empirical CDF vs. normal* plot. For example,
D = 0.105 means the two curves are at most 10.5 percentage points apart.

**p-value.** If H₀ is true, the distribution of Dₙ doesn't depend on which
continuous distribution is tested. For large n, √n·Dₙ follows the Kolmogorov
distribution:

```math
P\left(\sqrt{n}\, D_n \le t\right) \;\longrightarrow\; 1 - 2\sum_{k=1}^{\infty} (-1)^{k-1} e^{-2k^2 t^2}
```

`p_normal` is the probability of seeing a gap at least as large as the observed
one if the data really were normal: p = P(Dₙ ≥ D_observed | H₀). SciPy's `kstest`
computes this from the **exact** distribution of Dₙ for the actual n, so it is
valid for small samples too. The formula above is the large-n limit, useful for
intuition: at α = 0.05 the critical gap is about 1.36 / √n (≈ 0.18 for n = 60).

**Decision (`h0`).** This follows MATLAB's `[h, p] = kstest(...)` at α = 0.05:

| `h0` | Condition | Meaning |
|---|---|---|
| `1` | `p_normal < 0.05` | Normality **rejected**: the data deviates from normal more than chance explains |
| `0` | `p_normal ≥ 0.05` | Normality **not rejected**: no evidence against normality |

**Interpreting the result:**
- **`h0 = 0` doesn't prove normality.** It means the test found no evidence
  against it. With few samples (e.g. the 6-row reference file) the test can
  rarely reject anything.
- **With many samples, small deviations can reject normality** even when they
  don't matter in practice. Always look at the Q-Q plot and histogram as well.
- **The p-value is slightly optimistic.** WM and APD are estimated from the same
  data being tested, so the normal curve is already fitted to it and Dₙ comes out
  smaller than it would against a fixed distribution. The Lilliefors test corrects
  for this; the original MATLAB method is kept here.
- **The test assumes continuous data.** It isn't valid for integer data with many
  ties, which would always "fail". That's why it's **not run for discrete
  parameters** such as `noise`.

### Discrete parameters

A parameter is treated as **discrete** when every value is a whole number **and**
it has at most 15 distinct values (`MAX_DISCRETE_LEVELS` in
`statistical_data.py`). Integer data with a wide spread is better described by
the continuous statistics.

- **Mode:** the most frequent value. On a tie, the value closest to the median
  wins.
- **Mode share / off-mode share:** the fraction of samples at the mode, and its
  complement.
- **Rolling mode share:** the fraction of samples equal to the mode within a
  trailing window. The window is about n/10 samples, kept between 3 and 20.

### Histogram bins and density curves

- **Bin width** uses NumPy's `auto` rule: the narrower of two widths, so the bins
  adapt to each parameter's spread and sample size. The rule used is shown in the
  plot title.
  - **Freedman–Diaconis:** 2·IQR / n^(1/3); robust to outliers.
  - **Sturges:** range / (log₂ n + 1); suited to small samples.
- **KDE** (kernel density estimate, orange): a smoothed histogram from SciPy's
  `gaussian_kde`, scaled to counts. It shows the true shape, e.g. two peaks or a
  long tail.
- **Normal curve** (green, dashed): a normal distribution with mean WM and
  standard deviation APD, the same one the KS test uses. Where the KDE and this
  curve differ, the data isn't normal.

### Q-Q plot

The sorted values x(i) are plotted against the matching standard-normal quantiles
z. Normal data follows the line WM + APD·z.

| Pattern | Meaning |
|---|---|
| Points on the line | Normal-looking data |
| Both ends curve away from the line in opposite directions | Heavy tails |
| Points bend away on one side | Skew |
| A single point far from the line | Outlier |

### Correlation heatmap (Spearman ρ)

Spearman correlation is the Pearson correlation of the **ranks**. It measures
whether two parameters rise or fall together, without assuming a straight-line
relationship. It also isn't distorted by single outliers, and it works for the
integer `noise` column.

Values run from −1 (perfectly opposite) through 0 (unrelated) to +1 (perfectly
together). Pairs are computed on rows where both values exist; fewer than 3 shared
rows gives "n/a".

### Robust z-scores (overview box plot)

Each parameter is put on a common, unitless scale:

- **continuous:** z = (x − WM) / APD;
- **discrete:** z = (x − mode) / σ.

On this scale every parameter is centred at 0 with comparable spread, and outliers
of the continuous parameters lie beyond ±3.

## Sample data generator

`create_dummy_excel.py` writes a reproducible test file, `sample_measurements.xlsx`.
It uses the same layout as `reference_data.xlsx` (table at B3, columns `serial`,
`clock`, `p70`, `p140`, `noise`, `sfdr`) and has 60 rows.

The distributions:
- **`clock`:** normal with mean 13.0 and std 0.9, kept between 11 and 15 (values
  outside are redrawn), rounded to 2 decimal places;
- **`p70`, `p140`, `sfdr`:** normal distributions modelled on the reference data,
  rounded to 2 decimal places;
- **`noise`:** whole numbers, mostly −104, some −105, and occasionally −103.

The edge cases:
- an outlier in `clock` (row 4, value 20.00);
- blank cells in `clock` and `p140`;
- a text entry (`N/A`) in `p70`;
- serials with leading zeros (e.g. `020`).

```bash
python create_dummy_excel.py
```

Options: `python create_dummy_excel.py my_file.xlsx --rows 100 --seed 7`.

## Project files

| File | Purpose |
|---|---|
| `main.py` | Command line: loads the file, runs the analysis, prints results, opens/exports dashboards |
| `load_excel.py` | Finds and reads the measurement table |
| `statistical_data.py` | Continuous and discrete statistics, automatic type detection |
| `weighted_mean.py` | Weighted Mean (WM) |
| `absolute_pairwise_difference.py` | APD (Sₙ) |
| `dashboards.py` | Page drawing, the single-window viewer with navigation, Save and export |
| `create_dummy_excel.py` | Test data generator |
| `reference_data.xlsx` | Real reference measurements |
