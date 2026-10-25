#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["matplotlib"]
# ///

# How to run:
#   python3 plot_globalsc.py arrivals.csv

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import List, Sequence

import matplotlib

if __name__ == "__main__":
    matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_PATH = SCRIPT_DIR / "globalsc.pdf"
ARRIVAL_COLUMN = "arrival_offset_ms"


class CsvDataError(Exception):
    """Raised when an input CSV cannot provide valid arrival offsets."""


def read_arrival_offsets(path: Path) -> List[float]:
    values: List[float] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CsvDataError("%s: missing CSV header" % path)
        if ARRIVAL_COLUMN not in reader.fieldnames:
            raise CsvDataError(
                "%s: missing %r column" % (path, ARRIVAL_COLUMN)
            )

        for row_number, row in enumerate(reader, start=2):
            raw_value = row.get(ARRIVAL_COLUMN)
            if raw_value is None or not raw_value.strip():
                raise CsvDataError(
                    "%s:%d: missing %s value"
                    % (path, row_number, ARRIVAL_COLUMN)
                )
            try:
                value = float(raw_value)
            except ValueError as error:
                raise CsvDataError(
                    "%s:%d: invalid %s value %r"
                    % (path, row_number, ARRIVAL_COLUMN, raw_value)
                ) from error
            if not math.isfinite(value):
                raise CsvDataError(
                    "%s:%d: %s must be finite"
                    % (path, row_number, ARRIVAL_COLUMN)
                )
            values.append(value)

    if not values:
        raise CsvDataError("%s: no data rows" % path)
    return values


def draw_cdf(
    ax: Axes,
    values: Sequence[float],
    *,
    label_size: int = 18,
    x_tick_size: int = 14,
    y_tick_size: int = 16,
) -> None:
    ordered = sorted(values)
    cdf = [(index + 1) / len(ordered) for index in range(len(ordered))]

    ax.step(ordered, cdf, where="post", linewidth=2.25)
    ax.set_xlabel(
        "Arrival offset (ms)",
        fontweight="bold",
        fontsize=label_size,
    )
    ax.set_ylabel("CDF", fontweight="bold", fontsize=label_size)
    ax.set_ylim(0.0, 1.0)
    ax.tick_params(axis="x", labelsize=x_tick_size)
    ax.tick_params(axis="y", labelsize=y_tick_size)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")


def plot_cdf(
    values: Sequence[float],
    output_path: Path = OUTPUT_PATH,
) -> None:
    fig, ax = plt.subplots(figsize=(4.33, 2))
    draw_cdf(ax, values)
    fig.tight_layout()
    fig.savefig(output_path, format="pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot an arrival_offset_ms CDF from a CSV file."
    )
    parser.add_argument(
        "csv_file",
        metavar="CSV",
        type=Path,
        help="CSV file containing an arrival_offset_ms column",
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
        values = read_arrival_offsets(args.csv_file)
        plot_cdf(values, args.output)
    except (OSError, csv.Error, CsvDataError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    print("%s: %d values" % (args.csv_file, len(values)))
    print("PDF: %s" % args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
