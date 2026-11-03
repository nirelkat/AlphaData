"""Statistical analysis of product parameters (port of the main MATLAB script).

Loads the measurement sheet, analyses every parameter and opens one dashboard
window per parameter plus a final executive summary window:

    continuous parameters first (clock, p70, p140, sfdr - in sheet order),
    then discrete ones (noise), then the summary.

Usage:
    python main.py measurements.xlsx
    python main.py measurements.xlsx --export out/ --format pdf
    python main.py measurements.xlsx --export out/ --format png --no-show
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

from dashboards import (add_export_buttons, continuous_dashboard, discrete_dashboard,
                        save_figure, summary_dashboard)
from load_excel import PARAMETER_COLUMNS, SERIAL_COLUMN, load_excel
from statistical_data import analyse


def print_continuous(st, serials):
    """MATLAB displayed the statisticalData outputs (no semicolon)."""
    print(f"--- {st.name} (continuous) ---")
    print(f"average  = {st.average:.4f}")
    print(f"Median   = {st.median:.4f}")
    print(f"WM       = {st.wm:.4f}")
    print(f"sigma    = {st.sigma:.4f}")
    print(f"APD      = {st.apd:.4f}")
    print(f"skewness = {st.skewness:.3f}   excess kurtosis = {st.kurtosis:.3f}")
    print(f"h0       = {st.h0:g}   (1 = normality rejected at alpha = 0.05)")
    print(f"p_normal = {st.p_normal:.4g}   (KS D = {st.ks_statistic:.4f})")
    print(f"outliers = {_outlier_text(st.outliers, serials)}\n")


def print_discrete(st, serials):
    print(f"--- {st.name} (discrete) ---")
    print(f"mode     = {st.mode:g}  ({st.mode_share:.1%} of samples)")
    print(f"off-mode = {st.off_mode_share:.1%}")
    print("counts   = " + ", ".join(f"{v:g}: {c}" for v, c in zip(st.values, st.counts)))
    print(f"outliers = {_outlier_text(st.outliers, serials)}   "
          f"(|x - mode| > {st.band:.3g})\n")


def print_summary(results, order):
    continuous = [n for n in order if results[n].kind == "continuous"]
    discrete = [n for n in order if results[n].kind == "discrete"]
    if continuous:
        print("=== Summary: continuous parameters ===")
        print(f"{'parameter':<10}{'mean':>10}{'median':>10}{'WM':>10}{'sigma':>9}"
              f"{'APD':>9}{'h0':>5}{'p_normal':>10}{'outliers':>10}")
        for name in continuous:
            s = results[name]
            print(f"{name:<10}{s.average:>10.3f}{s.median:>10.3f}{s.wm:>10.3f}"
                  f"{s.sigma:>9.3f}{s.apd:>9.3f}{s.h0:>5g}{s.p_normal:>10.3g}"
                  f"{int(s.outliers.sum()):>10}")
    if discrete:
        print("\n=== Summary: discrete parameters ===")
        print(f"{'parameter':<10}{'mode':>8}{'mode %':>9}{'off-mode %':>12}"
              f"{'distinct':>10}{'outliers':>10}")
        for name in discrete:
            s = results[name]
            print(f"{name:<10}{s.mode:>8g}{s.mode_share:>9.1%}{s.off_mode_share:>12.1%}"
                  f"{s.values.size:>10}{int(s.outliers.sum()):>10}")


def _outlier_text(mask, serials):
    flagged = ", ".join(serials[mask]) if mask.any() else "none"
    return f"{int(mask.sum())}  (serials: {flagged})"


def build_pages(test, results, source):
    """Create the dashboard figures in display order; returns [(slug, fig)]."""
    continuous = [n for n in PARAMETER_COLUMNS if n in results and results[n].kind == "continuous"]
    discrete = [n for n in PARAMETER_COLUMNS if n in results and results[n].kind == "discrete"]
    order = continuous + discrete
    total = len(order) + 1
    serials = test[SERIAL_COLUMN].to_numpy(dtype=str)

    pages = []
    for page, name in enumerate(order, start=1):
        builder = continuous_dashboard if name in continuous else discrete_dashboard
        fig = builder(test[name].to_numpy(dtype=float), serials, results[name],
                      f"{page}/{total}", source)
        pages.append((f"{page:02d}_{name}", fig))
    summary = summary_dashboard(test, results, order, f"{total}/{total}", source)
    pages.append((f"{total:02d}_summary", summary))
    return order, pages


def export_pages(pages, export_dir, fmt, stem):
    """Save every page; for PDF also one combined multi-page report."""
    from matplotlib.backends.backend_pdf import PdfPages

    export_dir = Path(export_dir)
    formats = ["png", "pdf"] if fmt == "both" else [fmt]
    for slug, fig in pages:
        for ext in formats:
            print(f"Saved {save_figure(fig, export_dir / f'{stem}_{slug}.{ext}')}")
    if "pdf" in formats:
        report = export_dir / f"{stem}_report.pdf"
        with PdfPages(report) as pdf:
            for _slug, fig in pages:
                hidden = [b.ax for b in getattr(fig, "_export_buttons", [])]
                hidden += [getattr(fig, "_export_status")] if hasattr(fig, "_export_status") else []
                for artist in hidden:
                    artist.set_visible(False)
                pdf.savefig(fig, facecolor=fig.get_facecolor())
                for artist in hidden:
                    artist.set_visible(True)
        print(f"Saved {report}  (all pages)")


def main():
    parser = argparse.ArgumentParser(description="Statistical analysis of product parameters.")
    parser.add_argument("excel_file",
                        help="Excel file with columns serial, clock, p70, p140, noise, sfdr")
    parser.add_argument("--sheet", default=0, help="Sheet name or index (default: first sheet)")
    parser.add_argument("--export", metavar="DIR",
                        help="Save every dashboard to DIR (also the folder used by the "
                             "Save buttons; default: <excel name>_dashboards next to the file)")
    parser.add_argument("--format", choices=["png", "pdf", "both"], default="pdf",
                        help="Format for --export (default: pdf, plus a combined report)")
    parser.add_argument("--no-show", action="store_true",
                        help="Do not open the dashboard windows (use with --export)")
    args = parser.parse_args()

    # MATLAB: clear; close all; clc
    plt.close("all")

    # MATLAB: loadExcel
    excel = Path(args.excel_file)
    test = load_excel(excel, sheet_name=args.sheet)
    serials = test[SERIAL_COLUMN].to_numpy(dtype=str)

    # MATLAB: statisticalData(clock, 'clock') - now for every parameter, with the
    # discrete or continuous analysis chosen automatically per column.
    results = {}
    for name in PARAMETER_COLUMNS:
        try:
            results[name] = analyse(test[name].to_numpy(dtype=float), name)
        except ValueError as err:  # e.g. a column with no numeric values
            print(f"--- {name} --- skipped: {err}\n")
    if not results:
        raise SystemExit("No parameter contains numeric data.")

    order, pages = build_pages(test, results, excel.name)
    for name in order:
        printer = print_continuous if results[name].kind == "continuous" else print_discrete
        printer(results[name], serials)
    print_summary(results, order)
    print()

    export_dir = Path(args.export) if args.export else excel.with_name(f"{excel.stem}_dashboards")
    for slug, fig in pages:
        add_export_buttons(fig, export_dir, f"{excel.stem}_{slug}")
    if args.export:
        export_pages(pages, export_dir, args.format, excel.stem)

    if not args.no_show:
        # One window per page; all stay open until closed.
        plt.show()


if __name__ == "__main__":
    main()
