#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_LOG_DIR = SCRIPT_DIR / "dilation_factor"
OUTPUT_PATH = SCRIPT_DIR / "evaluation-dilation-large-scale-limited-compute.pdf"

LOG_FILENAME = re.compile(r"(\d+)_dilation_factor\.log")
AVERAGE_DILATION = re.compile(r"Average dilation factor: ([\d.]+)")

DilationData = Tuple[List[int], List[float]]


class DilationDataError(Exception):
    """Raised when no dilation-factor data can be read."""


def read_dilation_factors(log_dir: Path = DEFAULT_LOG_DIR) -> DilationData:
    data = []

    for path in log_dir.iterdir():
        match = LOG_FILENAME.fullmatch(path.name)
        if match is None or not path.is_file():
            continue

        content = path.read_text(encoding="utf-8")
        average_match = AVERAGE_DILATION.search(content)
        if average_match is not None:
            data.append((int(match.group(1)), float(average_match.group(1))))

    if not data:
        raise DilationDataError(
            "%s: no dilation-factor log data found" % log_dir
        )

    scales, dilation_factors = zip(*sorted(data))
    return list(scales), list(dilation_factors)


def draw_fig18(
    ax: Axes,
    data: DilationData,
    *,
    compact: bool = False,
) -> None:
    scales, dilation_factors = data
    label_size = 12 if compact else 18
    tick_size = 12 if compact else 16
    y_label = "Dilation\nFactor" if compact else "Dilation Factor"
    x_label = "Scale (#gNB/#UE)" if compact else "Scale (#UEs or #gNBs)"

    ax.plot(scales, dilation_factors, marker="o", linestyle="-")
    ax.set_xlabel(
        x_label,
        fontsize=label_size,
        fontweight="bold",
    )
    ax.set_ylabel(y_label, fontsize=label_size, fontweight="bold")
    ax.set_xlim(0, 10500)
    ax.set_ylim(0, 300)
    if compact:
        ax.set_xticks([0, 5000, 10000], labels=["0", "5k", "10k"])
        ax.set_yticks([0, 150, 300])
    ax.grid(True, linestyle="--", linewidth=0.5)
    ax.tick_params(axis="both", labelsize=tick_size)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")


def save_fig18(
    data: DilationData,
    output_path: Path = OUTPUT_PATH,
    *,
    show: bool = False,
) -> None:
    fig, ax = plt.subplots(figsize=(6, 3))
    draw_fig18(ax, data)
    fig.tight_layout()
    fig.savefig(output_path)
    if show:
        plt.show()
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plot dilation factor against experiment scale."
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help="directory containing *_dilation_factor.log files",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_PATH,
        help="output PDF path",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="save the figure without opening a display window",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = read_dilation_factors(args.log_dir)
        save_fig18(data, args.output, show=not args.no_show)
    except (OSError, DilationDataError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
