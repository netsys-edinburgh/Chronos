#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Sequence

import matplotlib

if __name__ == "__main__":
    matplotlib.use("Agg")

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from globalsc_cdf.plot_globalsc import (  # noqa: E402
    CsvDataError,
    draw_cdf,
    read_arrival_offsets,
)
from fig18.plot_fig18 import (  # noqa: E402
    DEFAULT_LOG_DIR,
    DilationData,
    DilationDataError,
    draw_fig18,
    read_dilation_factors,
)
import matplotlib.pyplot as plt  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_GLOBALSC_CSV = REPOSITORY_ROOT / "globalsc_cdf" / "10k.csv"
OUTPUT_PATH = SCRIPT_DIR / "fig9c.pdf"


def save_combined_figure(
    arrival_offsets: Sequence[float],
    dilation_data: DilationData,
    output_path: Path = OUTPUT_PATH,
) -> None:
    fig, outer_ax = plt.subplots(figsize=(3.6, 3))
    draw_cdf(
        outer_ax,
        arrival_offsets,
        label_size=14,
        x_tick_size=12,
        y_tick_size=12,
    )
    fig.tight_layout()

    inset_ax = outer_ax.inset_axes([0.40, 0.25, 0.55, 0.36])
    draw_fig18(inset_ax, dilation_data, compact=True)

    fig.savefig(output_path, format="pdf", dpi=300)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot the Globalsc arrival CDF with Figure 18 inset."
    )
    parser.add_argument(
        "--globalsc-csv",
        type=Path,
        default=DEFAULT_GLOBALSC_CSV,
        help="CSV containing an arrival_offset_ms column",
    )
    parser.add_argument(
        "--fig18-log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="directory containing Figure 18 dilation-factor logs",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="output PDF path",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        arrival_offsets = read_arrival_offsets(args.globalsc_csv)
        dilation_data = read_dilation_factors(args.fig18_log_dir)
        save_combined_figure(arrival_offsets, dilation_data, args.output)
    except (OSError, csv.Error, CsvDataError, DilationDataError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    print("PDF: %s" % args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
