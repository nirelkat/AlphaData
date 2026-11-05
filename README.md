# AlphaData – parameter distribution analysis

## Purpose

This project aims to conduct an **exploratory data analysis on electronic product
metrics** to understand their statistical distribution, evaluate whether they
follow a normal distribution, and set clear acceptance thresholds for quality
assurance.

How the tool serves each of these three goals:

| Goal | How it is addressed |
|---|---|
| **Understand each metric's distribution** | One dashboard page per metric: data in production order, histogram with a smoothed density curve, cumulative distribution and summary statistics. Robust statistics (WM, APD) describe the bulk of the data without being pulled by a few bad units |
| **Evaluate normality** | The Kolmogorov–Smirnov test (`h0`, `p_normal`) together with the Q-Q plot, skewness and kurtosis. See [The Kolmogorov-Smirnov test explained](#the-kolmogorov-smirnov-test-explained) for what the test can and can't tell you |
| **Set acceptance thresholds** | Data-driven limits per metric: **WM ± 3·APD** for continuous metrics and **mode ± max(3σ, 1)** for integer metrics such as `noise`. Units outside the limits are listed by serial number |

The acceptance thresholds here are **statistical**. They describe what is normal
for the population that was measured, not what the product specification allows.
They are only as trustworthy as the normality assessment behind them (see
[Why normality matters for the thresholds](#why-normality-matters-for-the-thresholds)).

## What it does

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

The KS test checks whether a continuous parameter is consistent with a normal
distribution centred on WM with spread APD:
- **D:** the largest vertical gap between the data's cumulative distribution and
  the normal one.
- **`p_normal`:** how often a truly normal sample would show a gap at least that
  large.
- **`h0`:** `1` when `p_normal < 0.05` (normality rejected), `0` otherwise
  (not rejected).

It isn't run for discrete parameters such as `noise`. The full explanation, a
worked example and the test's limitations are in
[The Kolmogorov-Smirnov test explained](#the-kolmogorov-smirnov-test-explained).

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

## The Kolmogorov-Smirnov test explained

This section explains what the KS test (`kstest`) does step by step, how to read
its two outputs `h0` and `p_normal`, and where it can mislead you.

### 1. The question it answers

*"If this metric really followed a normal distribution, would a sample like mine
be unusual?"*

The test never proves that data is normal. It can only find evidence that it
**isn't**. Formally it weighs two hypotheses:

| Hypothesis | Statement |
|---|---|
| H₀ (null) | The values come from a normal distribution with mean WM and standard deviation APD |
| H₁ (alternative) | They come from some other distribution |

### 2. Why it compares cumulative distributions, not histograms

A histogram depends on the choice of bins: the same data can look normal with one
bin width and lumpy with another. The **cumulative distribution function (CDF)**
needs no such choice. For any value x it gives the fraction of values ≤ x, a curve
that rises from 0 to 1.

The KS test compares two CDFs:

- **Empirical CDF Fₙ (the data):** a staircase. Sort the n values; the curve jumps
  up by 1/n at each one. After the i-th smallest value it stands at i/n.
- **Reference CDF Φ (the model):** the smooth S-shaped CDF of the normal
  distribution. Each value is first standardised as zᵢ = (xᵢ − WM) / APD, so the
  reference is the standard normal.

If the data is normal, the staircase hugs the S-curve and the gaps between them
are small. You can see both curves in the *Empirical CDF vs. normal* plot on every
continuous page.

### 3. The test statistic D: the largest gap

```math
D_n = \sup_{z} \left| F_n(z) - \Phi(z) \right|
```

D is the **largest vertical distance** between the two curves anywhere on the
axis. It is a fraction: D = 0.105 means that at some value the data and the model
disagree by 10.5 percentage points about how much of the population lies below it.

The staircase only changes at the data points, and Φ only rises, so the largest
gap must occur right at a step: just before it or just after it. That makes D
easy to compute exactly. With the values sorted, z(1) ≤ … ≤ z(n):

```math
D^{+} = \max_{i} \left( \frac{i}{n} - \Phi\left(z_{(i)}\right) \right)
\qquad
D^{-} = \max_{i} \left( \Phi\left(z_{(i)}\right) - \frac{i-1}{n} \right)
\qquad
D_n = \max\left(D^{+},\, D^{-}\right)
```

- **D⁺:** the data has more values below a point than the model expects (the
  staircase is **above** the curve).
- **D⁻:** the data has fewer (the staircase is **below** the curve).

### 4. Worked example: `clock` in `reference_data.xlsx`

The six `clock` values have WM = 14.476 and APD = 0.727. Each value is
standardised, and the staircase is compared with Φ just before and just after its
step:

| i | Serial | clock | z = (x − WM)/APD | Φ(z) | Staircase before step, (i−1)/n | Staircase after step, i/n | Gap after = i/n − Φ | Gap before = Φ − (i−1)/n |
|---|---|---|---|---|---|---|---|---|
| 1 | 201 | 11.80 | −3.678 | 0.000 | 0.000 | 0.167 | 0.167 | 0.000 |
| 2 | 144 | 12.30 | −2.991 | 0.001 | 0.167 | 0.333 | **0.332** | −0.165 |
| 3 | 931 | 14.40 | −0.104 | 0.458 | 0.333 | 0.500 | 0.042 | 0.125 |
| 4 | 450 | 14.60 | +0.170 | 0.568 | 0.500 | 0.667 | 0.099 | 0.068 |
| 5 | 020 | 14.90 | +0.583 | 0.720 | 0.667 | 0.833 | 0.113 | 0.053 |
| 6 | 256 | 15.01 | +0.734 | 0.769 | 0.833 | 1.000 | 0.231 | −0.065 |

D⁺ = 0.332 (at serial 144) and D⁻ = 0.125, so **D = 0.332**.

In words: 2 of the 6 units (33%) have a clock of 12.30 or less, but the fitted
normal model expects only 0.1% of units that low. The question is whether a
33-point disagreement is surprising for a sample of only six. Section 6 answers
it.

### 5. Why one yardstick works for every distribution

D would be useless if its typical size depended on the distribution being tested.
It doesn't, thanks to the **probability integral transform**: if X really follows
a continuous distribution with CDF F, then F(X) is uniformly distributed between 0
and 1. Under H₀, the values Φ(zᵢ) therefore behave like n uniform random numbers,
whatever distribution was hypothesised.

So the behaviour of D when H₀ is true depends **only on n**. That is why one table
of critical values (or one formula) serves every KS test. The test is
**distribution-free**.

### 6. From D to a p-value

**p-value.** `p_normal` answers: *if the data really were normal, how often would
a sample of this size show a gap at least as large as the one observed?*

```math
p = P\left(D_n \ge D_{\text{observed}} \mid H_0\right)
```

**Exact computation.** SciPy computes this from the **exact** distribution of Dₙ
for the actual n (the `kstwo` distribution), so it is valid for small samples too.

**Large-n approximation.** For large n, √n·Dₙ follows the Kolmogorov
distribution:

```math
P\left(\sqrt{n}\, D_n \le t\right) \;\longrightarrow\; 1 - 2\sum_{k=1}^{\infty} (-1)^{k-1} e^{-2k^2 t^2}
```

This gives the familiar rule of thumb: at α = 0.05 the critical gap is about
1.36 / √n.

**Critical values (exact).** H₀ is rejected at α = 0.05 when D exceeds:

| n | 6 | 10 | 20 | 30 | 60 | 100 | 200 |
|---|---|---|---|---|---|---|---|
| Critical D | 0.519 | 0.409 | 0.294 | 0.242 | 0.172 | 0.134 | 0.095 |

**Worked example, continued.** For the six `clock` values, D = 0.332 is well
below the critical 0.519, and p = 0.428: about 43% of genuinely normal samples of
six would show a gap this large. So `h0 = 0`, normality is not rejected.

Note how much room small samples get. With six values, the curves may disagree by
up to 52 percentage points before the test objects.

### 7. The decision: `h0`

| `h0` | Condition | Meaning |
|---|---|---|
| `1` | `p_normal < 0.05` | Normality **rejected**: a gap this large would be rare (under 5%) if the data were normal |
| `0` | `p_normal ≥ 0.05` | Normality **not rejected**: the data is *compatible* with normal. That isn't proof that it is normal |

This follows MATLAB's `[h, p] = kstest(...)`. α = 0.05 is the false-alarm rate you
accept, and two kinds of mistake are possible:

| | Data really normal | Data really not normal |
|---|---|---|
| `h0 = 1` (reject) | **False alarm** (type I error). Happens at most α = 5% of the time | Correct detection |
| `h0 = 0` (don't reject) | Correct | **Missed departure** (type II error). Common with small n, see section 10 |

The chance of correctly detecting a non-normal metric is called the test's
**power**. It grows with sample size and with how far the data departs from normal.

### 8. What the KS test is sensitive to, and what it misses

**It looks hardest at the middle of the distribution.** The random wobble of the
staircase is largest at the median and small in the tails. Its standard deviation
at a point where the true CDF equals F is √(F(1−F)/n). For n = 60:

| Position | Typical wobble of the staircase |
|---|---|
| Median (F = 0.5) | 0.065 |
| 1% / 99% tail (F = 0.01 / 0.99) | 0.013 |

D treats a 0.03 gap the same wherever it occurs. In the tails, a gap of 0.03 is
already more than twice the normal wobble, a strong sign, yet it is far below the
critical 0.172. **Tail problems such as too many extreme units are what KS detects
worst**, and in quality assurance those are often what matters most.

**A single outlier barely moves D.** One value can shift the staircase by at most
1/n (0.017 for n = 60). The KS test is therefore no outlier detector; that is the
job of the WM ± 3·APD band.

### 9. How this program's setup affects the test

- **The reference normal is fitted to the same data.** WM and APD are estimated
  from the values being tested, so the model curve is already pulled toward the
  data. D comes out smaller than it would against an independently known
  distribution, and the p-values are **too large**, making the test conservative.
  The textbook correction for this situation (estimated mean and σ) is the
  **Lilliefors test**. The original MATLAB method is kept here.
- **Robust centre and spread.** Using WM and APD instead of mean and σ keeps
  outliers from distorting the model curve. Outliers then show up as large z
  values (serials 201 and 144 above sit at z ≈ −3.7 and −3.0).
- **APD = 0 fallback.** If APD is 0, σ is used instead (see
  [When APD is 0](#when-apd-is-0-console-warning)).
- **Not used for discrete data.** The test assumes continuous data. Integer
  metrics such as `noise` have many tied values, so their staircase moves in a
  few big jumps and the test would reject almost automatically. It is skipped
  for them.

### 10. How reliable is it here? (simulation)

To measure the real behaviour, many random samples were generated with a known
shape and rounded to 2 decimal places like the real data. Each was run through
this program's KS test and three alternatives. The table shows how often each
method **rejected normality** (seed 2, 800 samples per cell):

| Data actually is … | n | This program (KS, WM/APD) | KS with mean/σ | Shapiro–Wilk | Anderson–Darling |
|---|---|---|---|---|---|
| Normal (should reject ≈ 5%) | 20 | 3% | 0% | 4% | 5% |
| Heavy-tailed (t, 3 d.f.) | 20 | 3% | 3% | 34% | 32% |
| Skewed (log-normal) | 20 | 5% | 4% | 68% | 61% |
| Flat (uniform) | 20 | 7% | 0% | 19% | 16% |
| Normal (should reject ≈ 5%) | 60 | 0% | 0% | 4% | 5% |
| Heavy-tailed (t, 3 d.f.) | 60 | 1% | 12% | 71% | 67% |
| Skewed (log-normal) | 60 | 17% | 32% | 99% | 99% |
| Flat (uniform) | 60 | 3% | 0% | 85% | 69% |

With 6 values (like `reference_data.xlsx`) this program rejected in under 1% of
cases whatever the true shape.

What this means:

- **False alarms are rare.** When this program says "not normal" (`h0 = 1`), take
  it seriously: the data is very likely not normal.
- **Missed departures are common.** `h0 = 0` is **weak evidence**. Even with 60
  units, clearly heavy-tailed or flat data passed more than 95% of the time.
- **Better tools exist for the normality goal.** Shapiro–Wilk and Anderson–Darling
  keep the false-alarm rate near 5% while detecting real departures far more often.
  Anderson–Darling in particular weights the tails more heavily, where QA
  thresholds live.

The simulation can be reproduced with SciPy (`scipy.stats.shapiro`,
`scipy.stats.anderson`) and `statistical_data.statistical_data`.

### 11. Reading the result together with the plots

| KS result | Q-Q plot / histogram | Conclusion |
|---|---|---|
| `h0 = 1` | Clear curve or skew | Not normal. Treat the 3·APD thresholds with care |
| `h0 = 1` | Looks straight, large n | Possibly a small deviation that a large sample can detect; judge whether it matters in practice |
| `h0 = 0` | Straight line, symmetric histogram, skewness and kurtosis near 0 | Consistent with normal |
| `h0 = 0` | Curved ends, long tail, or skewness/kurtosis far from 0 | Probably **not** normal; the test lacked power (section 10) |
| `h0 = 0` | Few samples (under ~20) | Inconclusive; collect more data |

### 12. Other assumptions to keep in mind

- **Independent, identically distributed samples.** The test assumes every unit
  comes from the same, unchanging process. A drift over production order (visible
  in the *Data vs. sample* plot) breaks this. A mixture of two batches can look
  "not normal" even when each batch is normal.
- **Several tests at once.** Four continuous metrics are tested, each with a 5%
  false-alarm risk. Even if all four are perfectly normal, the chance that at least
  one gets `h0 = 1` by luck is 1 − 0.95⁴ ≈ 18.5% (less in practice here, because
  this setup is conservative).
- **Sample size.** With very few units the test can hardly reject anything. With
  very many it flags deviations too small to matter.

### Why normality matters for the thresholds

The acceptance band WM ± 3·APD is meaningful because, **for normal data**, it
contains 99.73% of units. That means about 0.16 good units flagged per 60 measured,
essentially none.

If a metric is not normal, that promise breaks:
- **Heavy tails:** more good units fall outside the band (false rejects), or the
  band ends up too wide to catch real defects.
- **Skew:** the band is too tight on one side and too loose on the other.

This is why the normality assessment comes before trusting the thresholds, and
why, given section 10, the Q-Q plot and skewness/kurtosis should always be read
alongside `h0`.

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
