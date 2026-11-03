"""Dashboards: one page per parameter plus an executive summary page.

All pages are shown in ONE window (DashboardViewer) with a navigation bar:
    [<]  [clock] [p70] [p140] [sfdr] [noise] [Summary]  [>]   [Save PNG] [Save PDF]
Keyboard: Left/Right arrows or PageUp/PageDown, Home/End, digits 1-9.

Continuous parameter page (2 x 2 plots + statistics panel):
    data vs. sample index | histogram (automatic bins) + density curves
    empirical CDF vs. normal | normal Q-Q plot

Discrete parameter page (2 x 2 plots + statistics panel):
    data vs. sample index (integer ticks, side count bars, rolling mode share)
    bar chart with count/percentage labels | cumulative distribution
    frequency table

Summary page:
    continuous summary table, discrete summary table,
    Spearman correlation heatmap, overview box plot (robust z-scores)

Each page builder draws into a figure it is given, so the same code renders
a page inside the viewer window and into a separate figure for export
(save_page / export_pages).
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.widgets import Button
from scipy import stats

# ---- Palette (validated reference palette, light surface) ------------------
SURFACE = "#fcfcfb"
PANEL = "#f4f3ef"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GRID = "#e4e3de"
DATA = "#2a78d6"  # series 1 - measurements
MEAN = "#eb6834"  # series 2 - mean / KDE / mode
WM_COLOR = "#1baf7a"  # series 3 - WM / normal reference
OUTLIER = "#d03b3b"  # status "critical" - always shipped with a label
MODE_FILL = "#fbe3d8"  # light orange - mode row in the frequency table
OUTLIER_FILL = "#f7dcdc"  # light red - outlier row in the frequency table
DIVERGING = LinearSegmentedColormap.from_list(
    "blue_gray_red", ["#2a78d6", "#f0efec", "#e34948"])

FIGSIZE = (16, 9)
MAX_SERIALS_SHOWN = 8  # outlier serials listed in the statistics panel
MAX_ANNOTATED = 8  # outliers labelled with their serial in the plots

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": INK_SECONDARY,
    "axes.labelcolor": INK,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.labelsize": 9,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "legend.frameon": False,
    "text.color": INK,
})


# =========================================================================== #
# Continuous parameter page
# =========================================================================== #
def continuous_dashboard(fig, values, serials, st, page_label, source):
    """Draw the page of a continuous parameter into ``fig`` (``st``: ContinuousStats)."""
    x = np.asarray(values, dtype=float)
    valid = x[~np.isnan(x)]
    ax_data, ax_hist, ax_cdf, ax_qq, ax_panel = _page_layout(
        fig, f"{st.name}  -  continuous parameter", page_label, source)
    scale_ok = np.isfinite(st.scale) and st.scale > 0
    index = np.arange(1, x.size + 1)

    # ---- Data vs. sample index (MATLAB figure 1) ---------------------------
    if scale_ok:
        ax_data.axhspan(st.band_low, st.band_high, color=DATA, alpha=0.07, lw=0,
                        label=f"WM ± 3·{st.scale_name}")
    ax_data.scatter(index[~st.outliers], x[~st.outliers], s=26, color=DATA,
                    edgecolor=SURFACE, linewidth=0.8, zorder=3, label="data")
    ax_data.scatter(index[st.outliers], x[st.outliers], s=40, color=OUTLIER,
                    edgecolor=SURFACE, linewidth=0.8, zorder=4, label="outlier")
    ax_data.axhline(st.average, color=MEAN, ls="--", lw=1.6, label="mean")
    ax_data.axhline(st.wm, color=WM_COLOR, ls="--", lw=1.6, label="WM")
    _annotate_outliers(ax_data, index, x, st.outliers, serials)
    ax_data.margins(y=0.1)
    # MATLAB title: "<name> average = ..., <name> WM = ..."
    ax_data.set_title(f"Data vs. sample  (average = {st.average:.2f}, WM = {st.wm:.2f})")
    ax_data.set_xlabel("Sample index (row order)")
    ax_data.set_ylabel(st.name)
    ax_data.legend(loc="upper left", ncol=5, bbox_to_anchor=(0, -0.13))

    # ---- Histogram with automatic bins + density curves --------------------
    edges, rule = _auto_bins(valid)
    width = edges[1] - edges[0] if edges.size > 1 else 0.0
    ax_hist.hist(valid, bins=edges, color=DATA, alpha=0.8, edgecolor=SURFACE,
                 linewidth=2, label="count")
    grid = np.linspace(edges[0] - width, edges[-1] + width, 300)
    if valid.size >= 2 and np.ptp(valid) > 0:
        kde = stats.gaussian_kde(valid)
        ax_hist.plot(grid, kde(grid) * valid.size * width, color=MEAN, lw=2,
                     label="smoothed density (KDE)")
    if scale_ok:
        ax_hist.plot(grid, stats.norm.pdf(grid, st.wm, st.scale) * valid.size * width,
                     color=WM_COLOR, lw=1.6, ls="--",
                     label=f"normal (WM, {st.scale_name})")
    ax_hist.set_title(f"Histogram  ({len(edges) - 1} bins of {width:.3g}, {rule} rule)")
    ax_hist.set_xlabel(st.name)
    ax_hist.set_ylabel("Count")
    ax_hist.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax_hist.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, -0.13))

    # ---- Empirical CDF vs. normal CDF (MATLAB figure 3) --------------------
    sorted_x = np.sort(valid)
    ecdf = np.arange(1, sorted_x.size + 1) / sorted_x.size
    ax_cdf.step(np.r_[sorted_x[0], sorted_x], np.r_[0.0, ecdf], where="post",
                color=DATA, lw=2, label="empirical CDF")
    if scale_ok:
        xs = np.linspace(sorted_x[0], sorted_x[-1], 200)
        ax_cdf.plot(xs, stats.norm.cdf(xs, st.wm, st.scale), color=WM_COLOR, lw=1.6,
                    ls="--", label=f"normal CDF (WM, {st.scale_name})")
        ax_cdf.set_title(f"Empirical CDF vs. normal  (KS: D = {st.ks_statistic:.3f}, "
                         f"p = {st.p_normal:.3g})")
    else:
        ax_cdf.set_title("Empirical CDF")
    ax_cdf.set_xlabel(st.name)
    ax_cdf.set_ylabel("F(x)")
    ax_cdf.set_ylim(-0.02, 1.02)
    ax_cdf.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, -0.13))

    # ---- Normal Q-Q plot ---------------------------------------------------
    theoretical, ordered = stats.probplot(valid, dist="norm", fit=False)
    is_out = (ordered < st.band_low) | (ordered > st.band_high) if scale_ok \
        else np.zeros(ordered.shape, bool)
    ax_qq.scatter(theoretical[~is_out], ordered[~is_out], s=26, color=DATA,
                  edgecolor=SURFACE, linewidth=0.8, zorder=3, label="data")
    ax_qq.scatter(theoretical[is_out], ordered[is_out], s=40, color=OUTLIER,
                  edgecolor=SURFACE, linewidth=0.8, zorder=4, label="outlier")
    if scale_ok:
        z = np.array([theoretical.min(), theoretical.max()])
        ax_qq.plot(z, st.wm + st.scale * z, color=WM_COLOR, lw=1.6, ls="--",
                   label=f"normal reference: WM + {st.scale_name}·z")
    ax_qq.set_title("Normal Q-Q plot")
    ax_qq.set_xlabel("Theoretical normal quantile (z)")
    ax_qq.set_ylabel(f"Ordered {st.name} values")
    ax_qq.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, -0.13))

    # ---- Statistics panel ----------------------------------------------------
    out_serials = list(serials[st.outliers])
    _stats_panel(ax_panel, [
        ("Sample", None),
        ("Valid samples", f"{st.n}"),
        ("Missing / text cells", f"{st.missing}"),
        ("Location", None),
        ("Mean", _f(st.average)),
        ("Median", _f(st.median)),
        ("Weighted mean (WM)", _f(st.wm)),
        ("Spread", None),
        ("Std. deviation (σ)", _f(st.sigma)),
        ("APD (Sn)", _f(st.apd)),
        ("Min / max", f"{_f(sorted_x[0])} / {_f(sorted_x[-1])}"),
        ("Shape", None),
        ("Skewness", _f(st.skewness)),
        ("Excess kurtosis", _f(st.kurtosis)),
        (f"Outliers (WM ± 3·{st.scale_name})", None),
        ("Band", f"{_f(st.band_low)} … {_f(st.band_high)}"),
        ("Count", f"{len(out_serials)}"),
        ("Serials", _serial_list(out_serials)),
        ("Normality (KS test, α = 0.05)", None),
        ("D statistic", _f(st.ks_statistic)),
        ("p_normal", _f(st.p_normal, 3, g=True)),
        ("h0", _h0_text(st.h0)),
    ])
    return fig


# =========================================================================== #
# Discrete parameter page
# =========================================================================== #
def discrete_dashboard(fig, values, serials, st, page_label, source):
    """Draw the page of an integer-valued parameter into ``fig`` (``st``: DiscreteStats)."""
    x = np.asarray(values, dtype=float)
    cell_data, ax_bar, ax_cdf, ax_table, ax_panel = _page_layout(
        fig, f"{st.name}  -  discrete (integer) parameter", page_label, source,
        split_first=True)
    ax_data, ax_margin, ax_roll = cell_data
    index = np.arange(1, x.size + 1)
    mode_label = _f(st.mode, g=True)

    # Bar positions: the full integer range when short, else observed values.
    lo, hi = st.values.min(), st.values.max()
    if hi - lo <= 15:
        levels = np.arange(lo, hi + 1)
        counts = np.array([st.counts[st.values == v].sum() for v in levels])
    else:
        levels, counts = st.values, st.counts
    shares = counts / st.n
    level_is_outlier = np.abs(levels - st.mode) > st.band

    # ---- Data vs. sample index with side count bars ------------------------
    ax_data.axhline(st.mode, color=MEAN, ls="--", lw=1.4, alpha=0.8, zorder=1,
                    label=f"mode ({mode_label})")
    ax_data.scatter(index[~st.outliers], x[~st.outliers], s=26, color=DATA,
                    edgecolor=SURFACE, linewidth=0.8, zorder=3, label="data")
    ax_data.scatter(index[st.outliers], x[st.outliers], s=40, color=OUTLIER,
                    edgecolor=SURFACE, linewidth=0.8, zorder=4, label="outlier")
    _annotate_outliers(ax_data, index, x, st.outliers, serials)
    ax_data.set_title(f"Data vs. sample  (mode = {mode_label}, "
                      f"{st.mode_share:.0%} of samples)")
    ax_data.set_ylabel(st.name)
    ax_data.set_yticks(levels if levels.size <= 15 else
                       MaxNLocator(integer=True).tick_values(lo, hi))
    ax_data.set_ylim(lo - 0.6, hi + 0.6)
    ax_data.tick_params(labelbottom=False)
    ax_data.legend(loc="upper right", ncol=3, fontsize=7)

    ax_margin.barh(levels, counts, height=0.6, color=DATA, alpha=0.8)
    for level, count in zip(levels, counts):
        if count:
            ax_margin.text(count, level, f" {count}", va="center", fontsize=7,
                           color=INK_SECONDARY)
    ax_margin.set_xlim(0, counts.max() * 1.45)
    ax_margin.tick_params(labelleft=False, labelsize=7)
    ax_margin.set_xlabel("count", fontsize=8)
    ax_margin.grid(axis="y", visible=False)

    ax_roll.plot(index, st.rolling_mode_share * 100, color=MEAN, lw=1.8,
                 label=f"rolling share of {mode_label} ({st.rolling_window} samples)")
    ax_roll.axhline(st.mode_share * 100, color=INK_SECONDARY, ls=":", lw=1.2,
                    label=f"overall {st.mode_share:.0%}")
    ax_roll.set_ylim(-5, 105)
    ax_roll.set_ylabel("% at mode", fontsize=8)
    ax_roll.set_xlabel("Sample index (row order)")
    ax_roll.legend(loc="upper left", ncol=2, fontsize=7, bbox_to_anchor=(0, -0.62))

    # ---- Bar chart with count / percentage labels --------------------------
    colors = [OUTLIER if out else (MEAN if lvl == st.mode else DATA)
              for lvl, out in zip(levels, level_is_outlier)]
    ax_bar.bar(levels, counts, width=0.7, color=colors, edgecolor=SURFACE, linewidth=2)
    for level, count, share in zip(levels, counts, shares):
        ax_bar.text(level, count, f"{level:g}: {count} ({share:.0%})", ha="center",
                    va="bottom", fontsize=8 if levels.size <= 6 else 7,
                    rotation=0 if levels.size <= 6 else 90, color=INK)
    ax_bar.set_ylim(0, counts.max() * (1.18 if levels.size <= 6 else 1.6))
    ax_bar.set_xticks(levels if levels.size <= 15 else ax_bar.get_xticks())
    ax_bar.set_title("Value counts")
    ax_bar.set_xlabel(st.name)
    ax_bar.set_ylabel("Count")
    ax_bar.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax_bar.grid(axis="x", visible=False)
    _legend_patches(ax_bar, [(MEAN, "mode"), (DATA, "other values"),
                             (OUTLIER, "outlier values")])

    # ---- Cumulative distribution -------------------------------------------
    cumulative = np.cumsum(counts) / st.n * 100
    ax_cdf.step(np.r_[levels[0] - 1, levels], np.r_[0, cumulative], where="post",
                color=DATA, lw=2)
    ax_cdf.scatter(levels[counts > 0], cumulative[counts > 0], color=DATA, s=30,
                   zorder=3, edgecolor=SURFACE)
    for level, cum, count in zip(levels, cumulative, counts):
        if count:
            ax_cdf.annotate(f"{cum:.0f}%", (level, cum), textcoords="offset points",
                            xytext=(-4, 6), ha="right", fontsize=8, color=INK_SECONDARY)
    ax_cdf.set_xticks(levels if levels.size <= 15 else ax_cdf.get_xticks())
    ax_cdf.set_ylim(-3, 112)
    ax_cdf.set_title("Cumulative distribution")
    ax_cdf.set_xlabel(st.name)
    ax_cdf.set_ylabel("% of samples ≤ value")

    # ---- Frequency table -----------------------------------------------------
    ax_table.axis("off")
    ax_table.set_title("Frequency distribution")
    rows = [[f"{v:g}", f"{c}", f"{s:.1%}", f"{cu:.1f}%"]
            for v, c, s, cu in zip(levels, counts, shares, cumulative) if c]
    row_levels = [v for v, c in zip(levels, counts) if c]
    table = ax_table.table(cellText=rows, colLabels=["Value", "Count", "Share", "Cumulative"],
                           loc="upper center", cellLoc="center", bbox=[0.05, 0.0, 0.9, 0.95])
    _style_table(table)
    for r, level in enumerate(row_levels, start=1):
        fill = OUTLIER_FILL if abs(level - st.mode) > st.band else (
            MODE_FILL if level == st.mode else None)
        if fill:
            for c in range(4):
                table[r, c].set_facecolor(fill)

    # ---- Statistics panel ----------------------------------------------------
    out_serials = list(serials[st.outliers])
    _stats_panel(ax_panel, [
        ("Sample", None),
        ("Valid samples", f"{st.n}"),
        ("Missing / text cells", f"{st.missing}"),
        ("Distribution", None),
        ("Mode (most frequent)", mode_label),
        ("Mode share", f"{st.mode_share:.1%}"),
        ("Off-mode share", f"{st.off_mode_share:.1%}"),
        ("Distinct values", f"{st.values.size}"),
        ("Median", _f(st.median, g=True)),
        ("Min / max", f"{_f(lo, g=True)} / {_f(hi, g=True)}"),
        ("Std. deviation (σ)", _f(st.sigma)),
        ("Outliers", None),
        ("Rule", "|x − mode| > max(3σ, 1)"),
        ("Threshold", f"± {_f(st.band)} from {mode_label}"),
        ("Count", f"{len(out_serials)}"),
        ("Share", f"{len(out_serials) / st.n:.1%}"),
        ("Serials", _serial_list(out_serials)),
        ("Normality", None),
        ("KS test", "not applied"),
        ("Reason", "integer data"),
    ])
    return fig


# =========================================================================== #
# Summary page
# =========================================================================== #
def summary_dashboard(fig, test, results, parameter_order, page_label, source):
    """Draw the executive summary across all parameters into ``fig``."""
    fig.set_facecolor(SURFACE)
    fig.suptitle("Executive summary  -  all parameters", fontsize=15, fontweight="bold",
                 x=0.04, ha="left", y=0.965)
    _footer(fig, page_label, source)
    gs = fig.add_gridspec(2, 2, height_ratios=[0.72, 1.45], width_ratios=[1, 1.45],
                          left=0.05, right=0.98, top=0.9, bottom=0.11,
                          hspace=0.3, wspace=0.18)
    tables = gs[0, :].subgridspec(1, 2, width_ratios=[1.75, 1], wspace=0.06)
    ax_cont, ax_disc = fig.add_subplot(tables[0]), fig.add_subplot(tables[1])
    ax_corr, ax_box = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

    continuous = [n for n in parameter_order if results[n].kind == "continuous"]
    discrete = [n for n in parameter_order if results[n].kind == "discrete"]

    # ---- Continuous summary table -------------------------------------------
    ax_cont.axis("off")
    ax_cont.set_title("Continuous parameters", loc="left")
    rows = []
    for name in continuous:
        s = results[name]
        rows.append([name, s.n, _f(s.average), _f(s.median), _f(s.wm), _f(s.sigma),
                     _f(s.apd), _f(s.skewness, 2), _f(s.p_normal, 3, g=True),
                     _normal_verdict(s.h0), int(s.outliers.sum())])
    if rows:
        table = ax_cont.table(
            cellText=rows, colLabels=["Parameter", "n", "Mean", "Median", "WM", "σ",
                                      "APD", "Skew", "KS p", "Normal?", "Outliers"],
            loc="upper center", cellLoc="center", bbox=[0, 0.05, 1, 0.9])
        _style_table(table)
        for r, row in enumerate(rows, start=1):
            if row[-1]:
                table[r, 10].set_facecolor(OUTLIER_FILL)
    else:
        ax_cont.text(0.5, 0.5, "No continuous parameters", ha="center", va="center")

    # ---- Discrete summary table ---------------------------------------------
    ax_disc.axis("off")
    ax_disc.set_title("Discrete parameters", loc="left")
    rows = []
    for name in discrete:
        s = results[name]
        rows.append([name, s.n, _f(s.mode, g=True), f"{s.mode_share:.0%}",
                     f"{s.off_mode_share:.0%}", s.values.size, int(s.outliers.sum())])
    if rows:
        table = ax_disc.table(
            cellText=rows, colLabels=["Parameter", "n", "Mode", "Mode share",
                                      "Off-mode", "Distinct", "Outliers"],
            loc="upper center", cellLoc="center",
            bbox=[0, 0.95 - 0.18 * (len(rows) + 1), 1, 0.18 * (len(rows) + 1)])
        _style_table(table)
        for r, row in enumerate(rows, start=1):
            if row[-1]:
                table[r, 6].set_facecolor(OUTLIER_FILL)
    else:
        ax_disc.text(0.5, 0.5, "No discrete parameters", ha="center", va="center")

    # ---- Correlation heatmap (Spearman, all parameters) ---------------------
    corr = test[list(parameter_order)].corr(method="spearman", min_periods=3)
    image = ax_corr.imshow(corr.to_numpy(), cmap=DIVERGING, vmin=-1, vmax=1)
    ax_corr.set_xticks(range(len(corr)), corr.columns, rotation=0)
    ax_corr.set_yticks(range(len(corr)), corr.index)
    ax_corr.grid(False)
    for i in range(len(corr)):
        for j in range(len(corr)):
            r = corr.iat[i, j]
            ax_corr.text(j, i, "n/a" if np.isnan(r) else f"{r:.2f}", ha="center",
                         va="center", fontsize=9,
                         color="white" if abs(np.nan_to_num(r)) > 0.65 else INK)
    ax_corr.set_title("Correlation between parameters (Spearman ρ)")
    bar = fig.colorbar(image, ax=ax_corr, fraction=0.046, pad=0.03)
    bar.ax.tick_params(labelsize=8)
    bar.outline.set_visible(False)

    # ---- Overview box plot (robust z-scores) --------------------------------
    data, labels, flagged = [], [], []
    for name in parameter_order:
        s = results[name]
        x = test[name].to_numpy(dtype=float)
        if s.kind == "continuous":
            center, scale, how = s.wm, s.scale, f"(x − WM) / {s.scale_name}"
        else:
            center, scale, how = s.mode, s.sigma, "(x − mode) / σ"
        z = (x - center) / scale if np.isfinite(scale) and scale > 0 else x * 0.0
        data.append(z[~np.isnan(z)])
        flagged.append(z[s.outliers])
        labels.append(f"{name}\n{how}")
    box = ax_box.boxplot(data, patch_artist=True, widths=0.5, showfliers=False,
                         medianprops={"color": MEAN, "lw": 2},
                         whiskerprops={"color": INK_SECONDARY},
                         capprops={"color": INK_SECONDARY})
    for patch in box["boxes"]:
        patch.set(facecolor=DATA, alpha=0.18, edgecolor=DATA)
    rng = np.random.default_rng(0)  # fixed jitter so exports are reproducible
    for i, (z, out) in enumerate(zip(data, flagged), start=1):
        ax_box.scatter(i + rng.uniform(-0.12, 0.12, z.size), z, s=12, color=DATA,
                       alpha=0.55, zorder=3, linewidth=0)
        ax_box.scatter(i + rng.uniform(-0.12, 0.12, out.size), out, s=30,
                       color=OUTLIER, zorder=4, edgecolor=SURFACE, linewidth=0.8)
    for level, text in ((-3, "−3"), (3, "+3")):
        ax_box.hlines(level, 0.4, len(data) + 0.4, color=INK_SECONDARY, ls=":", lw=1)
        ax_box.text(len(data) + 0.48, level, text, va="center", fontsize=8,
                    color=INK_SECONDARY)
    ax_box.set_xticks(range(1, len(labels) + 1), labels, fontsize=8)
    ax_box.set_xlim(0.4, len(data) + 0.7)
    ax_box.set_ylabel("Robust z-score")
    ax_box.set_title("Overview: all parameters on a common scale", loc="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (DATA, OUTLIER, MEAN)]
    ax_box.legend(handles, ["samples", "outliers", "median"], loc="lower right",
                  bbox_to_anchor=(1, 1.0), ncol=3, fontsize=8)
    return fig


# =========================================================================== #
# Pages, export and the single-window viewer
# =========================================================================== #
@dataclass
class Page:
    slug: str  # file-name part, e.g. "01_clock"
    label: str  # navigation label, e.g. "clock" or "Summary"
    draw: Callable  # draw(fig) renders the page into a figure


def save_page(page, path):
    """Render ``page`` into a fresh figure (no navigation bar) and save it."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig = Figure(figsize=FIGSIZE, facecolor=SURFACE)
    page.draw(fig)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    return path


def export_pages(pages, export_dir, fmt, stem):
    """Save every page (headless); PDF export also writes one combined report."""
    export_dir = Path(export_dir)
    formats = ["png", "pdf"] if fmt == "both" else [fmt]
    for page in pages:
        for ext in formats:
            print(f"Saved {save_page(page, export_dir / f'{stem}_{page.slug}.{ext}')}")
    if "pdf" in formats:
        report = export_dir / f"{stem}_report.pdf"
        with PdfPages(report) as pdf:
            for page in pages:
                fig = Figure(figsize=FIGSIZE, facecolor=SURFACE)
                page.draw(fig)
                pdf.savefig(fig, facecolor=SURFACE)
        print(f"Saved {report}  (all pages)")


class DashboardViewer:
    """One window showing one page at a time, with page navigation and export.

    Navigation bar (bottom of the window):
        [<]  [clock] [p70] [p140] [sfdr] [noise] [Summary]  [>]   [Save PNG] [Save PDF]
    The active page's button is highlighted. Save writes the visible page
    (without the navigation bar) to ``export_dir``.
    Keyboard: Left/Right or PageUp/PageDown = previous/next page,
    Home/End = first/last page, 1-9 = jump to that page.
    """

    BAR_Y, BAR_H = 0.006, 0.032

    def __init__(self, pages, export_dir, file_stem, source):
        self.pages = pages
        self.export_dir = Path(export_dir)
        self.file_stem = file_stem
        self.source = source
        self.index = 0
        self._widgets = []
        # Free the arrow keys (matplotlib binds them to zoom history by default).
        for key, name in (("left", "keymap.back"), ("right", "keymap.forward")):
            plt.rcParams[name] = [k for k in plt.rcParams[name] if k != key]
        self.fig = plt.figure(figsize=FIGSIZE)
        self.fig.canvas.mpl_connect("key_press_event", self._on_key)
        self.show_page(0)

    def run(self):
        """Open the window and block until it is closed."""
        plt.show()

    # ---- navigation --------------------------------------------------------
    def show_page(self, index, status=""):
        self.index = index % len(self.pages)
        page = self.pages[self.index]
        for widget in self._widgets:
            widget.disconnect_events()
        self._widgets = []
        self.fig.clear()
        page.draw(self.fig)
        self._add_navigation()
        self._status = self.fig.text(0.985, 0.965, status, ha="right", va="center",
                                     fontsize=9, color=WM_COLOR)
        _window_title(self.fig, f"AlphaData - {page.label} "
                                f"({self.index + 1}/{len(self.pages)}) - {self.source}")
        self.fig.canvas.draw_idle()

    def next_page(self, _event=None):
        self.show_page(self.index + 1)

    def previous_page(self, _event=None):
        self.show_page(self.index - 1)

    def save(self, ext):
        page = self.pages[self.index]
        path = save_page(page, self.export_dir / f"{self.file_stem}_{page.slug}.{ext}")
        print(f"Saved {path}")
        self._status.set_text(f"Saved {path.name}  ->  {path.parent}")
        self.fig.canvas.draw_idle()
        return path

    # ---- controls ----------------------------------------------------------
    def _add_navigation(self):
        x = 0.012
        x = self._button(x, 0.03, "<", self.previous_page)
        x += 0.004
        for i, page in enumerate(self.pages):
            x = self._button(x, 0.058, page.label,
                             lambda _e, i=i: self.show_page(i), active=i == self.index)
        x += 0.004
        x = self._button(x, 0.03, ">", self.next_page)
        x += 0.02
        x = self._button(x, 0.066, "Save PNG", lambda _e: self.save("png"))
        self._button(x, 0.066, "Save PDF", lambda _e: self.save("pdf"))

    def _button(self, x, width, label, callback, active=False):
        ax = self.fig.add_axes([x, self.BAR_Y, width, self.BAR_H])
        color = DATA if active else PANEL
        button = Button(ax, label, color=color, hovercolor=color if active else GRID)
        button.label.set_fontsize(9)
        button.label.set_color(SURFACE if active else INK)
        if active:
            button.label.set_fontweight("bold")
        button.on_clicked(callback)
        self._widgets.append(button)  # keep a reference (widgets are weakly held)
        return x + width + 0.004

    def _on_key(self, event):
        key = event.key or ""
        if key in ("right", "pagedown"):
            self.next_page()
        elif key in ("left", "pageup"):
            self.previous_page()
        elif key == "home":
            self.show_page(0)
        elif key == "end":
            self.show_page(len(self.pages) - 1)
        elif key.isdigit() and 1 <= int(key) <= len(self.pages):
            self.show_page(int(key) - 1)


# =========================================================================== #
# Shared helpers
# =========================================================================== #
def _page_layout(fig, title, page_label, source, split_first=False):
    """2 x 2 plot grid on the left and a statistics panel on the right of ``fig``."""
    fig.set_facecolor(SURFACE)
    fig.suptitle(title, fontsize=15, fontweight="bold", x=0.04, ha="left", y=0.965)
    _footer(fig, page_label, source)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1, 0.58], left=0.05, right=0.985,
                          top=0.9, bottom=0.12, wspace=0.24, hspace=0.42)
    if split_first:
        sub = gs[0, 0].subgridspec(2, 2, width_ratios=[5, 1], height_ratios=[3, 1.3],
                                   wspace=0.04, hspace=0.08)
        ax_data = fig.add_subplot(sub[0, 0])
        ax_margin = fig.add_subplot(sub[0, 1], sharey=ax_data)
        ax_roll = fig.add_subplot(sub[1, 0], sharex=ax_data)
        first = (ax_data, ax_margin, ax_roll)
    else:
        first = fig.add_subplot(gs[0, 0])
    axes = [first, fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, 0]),
            fig.add_subplot(gs[1, 1]), fig.add_subplot(gs[:, 2])]
    return axes


def _footer(fig, page_label, source):
    fig.text(0.985, 0.018, f"{source}   ·   page {page_label}", ha="right",
             va="center", fontsize=8, color=INK_SECONDARY)


def _stats_panel(ax, rows):
    """Two-column metrics list; rows with value None are section headings."""
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.add_patch(plt.Rectangle((0, 0), 1, 1, color=PANEL, zorder=0))
    ax.text(0.05, 0.975, "Statistics", fontsize=12, fontweight="bold", va="top")
    headings = sum(1 for _, v in rows if v is None)
    step = min(0.043, 0.86 / (len(rows) + 0.35 * headings))
    y = 0.92
    for label, value in rows:
        if value is None:
            y -= step * 0.35
            ax.text(0.05, y, label, fontsize=9, fontweight="bold", va="top",
                    color=DATA)
        else:
            ax.text(0.07, y, label, fontsize=9, va="top", color=INK_SECONDARY)
            ax.text(0.95, y, value, fontsize=9, va="top", ha="right",
                    family="monospace", color=INK)
        y -= step


def _style_table(table):
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    for (r, _c), cell in table.get_celld().items():
        cell.set_edgecolor(GRID)
        if r == 0:
            cell.set_facecolor(PANEL)
            cell.set_text_props(fontweight="bold", color=INK)
        else:
            cell.set_facecolor(SURFACE)


def _annotate_outliers(ax, index, x, outliers, serials):
    if 0 < outliers.sum() <= MAX_ANNOTATED:
        for i, value, serial in zip(index[outliers], x[outliers], serials[outliers]):
            ax.annotate(serial, (i, value), textcoords="offset points", xytext=(6, 4),
                        fontsize=8, color=OUTLIER)


def _legend_patches(ax, items, loc="upper right"):
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c, _ in items]
    ax.legend(handles, [label for _, label in items], loc=loc, fontsize=7)


def _auto_bins(valid):
    """numpy 'auto' rule: the narrower of Freedman-Diaconis and Sturges."""
    edges = np.histogram_bin_edges(valid, bins="auto")
    if valid.size < 2 or np.ptp(valid) == 0:
        return edges, "single-value"
    iqr = np.subtract(*np.percentile(valid, [75, 25]))
    fd_width = 2 * iqr / valid.size ** (1 / 3)
    sturges_width = np.ptp(valid) / (np.log2(valid.size) + 1)
    rule = "Freedman–Diaconis" if 0 < fd_width < sturges_width else "Sturges"
    return edges, rule


def _window_title(fig, title):
    manager = getattr(fig.canvas, "manager", None)
    if manager is not None:
        manager.set_window_title(title)


def _f(value, digits=3, g=False):
    """Format a number for display; NaN becomes an en dash."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "–"
    return f"{value:.{digits}g}" if g else f"{value:.{digits}f}"


def _serial_list(serials):
    if not serials:
        return "none"
    shown = ", ".join(serials[:MAX_SERIALS_SHOWN])
    extra = len(serials) - MAX_SERIALS_SHOWN
    return shown + (f" +{extra} more" if extra > 0 else "")


def _h0_text(h0):
    if np.isnan(h0):
        return "– (not run)"
    return "1 (rejected)" if h0 else "0 (not rejected)"


def _normal_verdict(h0):
    if np.isnan(h0):
        return "–"
    return "no" if h0 else "yes"
