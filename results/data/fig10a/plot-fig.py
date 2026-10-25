#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["matplotlib"]
# ///

# How to run:
#   python3 plot_emane.py first.csv second.csv

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUTPUT_PATH = Path("fig10a.pdf")
WAIT_COLUMN = "wait_ms"


class CsvDataError(Exception):
    """Raised when an input CSV cannot provide valid wait_ms values."""


def read_wait_values(path: Path) -> List[float]:
    values: List[float] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise CsvDataError("%s: missing CSV header" % path)
        if WAIT_COLUMN not in reader.fieldnames:
            raise CsvDataError("%s: missing %r column" % (path, WAIT_COLUMN))

        for row_number, row in enumerate(reader, start=2):
            raw_value = row.get(WAIT_COLUMN)
            if raw_value is None or not raw_value.strip():
                raise CsvDataError(
                    "%s:%d: missing %s value" % (path, row_number, WAIT_COLUMN)
                )
            try:
                value = float(raw_value)
            except ValueError as error:
                raise CsvDataError(
                    "%s:%d: invalid %s value %r"
                    % (path, row_number, WAIT_COLUMN, raw_value)
                ) from error
            if not math.isfinite(value):
                raise CsvDataError(
                    "%s:%d: %s must be finite" % (path, row_number, WAIT_COLUMN)
                )
            values.append(value)

    if not values:
        raise CsvDataError("%s: no data rows" % path)
    return values


def plot_cdfs(datasets: Sequence[Tuple[Path, Sequence[float]]]) -> None:
    fig, ax = plt.subplots(figsize=(4.5, 3))
    for path, values in datasets:
        ordered = sorted(values)
        cdf = [(index + 1) / len(ordered) for index in range(len(ordered))]
        ax.step(
            ordered,
            cdf,
            where="post",
            linewidth=6.0,
            label=path.stem,
        )

    ax.set_xlabel("Processing (ms)", fontweight="bold", fontsize=20)
    ax.set_ylabel("CDF", fontweight="bold", fontsize=20)
    ax.set_ylim(0.0, 1.0)
    ax.tick_params(axis="x", labelsize=18)
    ax.tick_params(axis="y", labelsize=18)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    ax.legend(loc="lower right", prop={"weight": "bold", "size": 20})
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, format="pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot wait_ms CDFs from one or more CSV files."
    )
    parser.add_argument(
        "csv_files",
        metavar="CSV",
        nargs="+",
        type=Path,
        help="CSV file containing a wait_ms column",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        datasets = [(path, read_wait_values(path)) for path in args.csv_files]
        plot_cdfs(datasets)
    except (OSError, csv.Error, CsvDataError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    for path, values in datasets:
        print("%s: %d values" % (path, len(values)))
    print("PDF: %s" % OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
