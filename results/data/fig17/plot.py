#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["matplotlib"]
# ///

# How to run:
#   python3 plot_epoll.py first.csv second.csv

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUTPUT_PATH: Final = Path("fig17.pdf")
SEG1: Final = "seg1_kernel_to_wake_us"
SEG2A: Final = "seg2a_lock_blocked_us"
SEG2B_V3: Final = "seg2b_drain_us"
SEG2C: Final = "seg2c_fanout_us"
SEG2B_V2: Final = "seg2b_drain_other_us"
SEG2_V1: Final = "seg2_wake_to_dispatch_us"


class ProfileError(Exception):
    """Raised when a profiler CSV cannot provide epoll timing values."""


@dataclass(frozen=True)
class Schema:
    seg2_key: str
    description: str
    caveat: str


@dataclass(frozen=True)
class Dataset:
    path: Path
    values: Tuple[float, ...]
    schema: Schema
    dropped_misaligned: int
    dropped_missing_kernel: int
    dropped_invalid: int


def detect_schema(fieldnames: Sequence[str]) -> Schema:
    names = set(fieldnames)
    if {SEG2A, SEG2B_V3, SEG2C}.issubset(names):
        return Schema(
            SEG2B_V3,
            "v3 (epoll drain isolated from fan-out)",
            "",
        )
    if {SEG2A, SEG2B_V2}.issubset(names):
        return Schema(
            SEG2B_V2,
            "v2",
            "upper bound: seg2b still includes per-UE fan-out",
        )
    if SEG2_V1 in names:
        return Schema(
            SEG2_V1,
            "v1",
            "loose upper bound: seg2 also includes mutex wait and fan-out",
        )
    raise ProfileError("unrecognized profiler CSV: no seg2 columns found")


def load_dataset(path: Path) -> Dataset:
    values: List[float] = []
    dropped_misaligned = 0
    dropped_missing_kernel = 0
    dropped_invalid = 0
    row_count = 0

    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(
            line for line in handle if not line.startswith("#")
        )
        if reader.fieldnames is None:
            raise ProfileError("%s: missing CSV header" % path)
        schema = detect_schema(reader.fieldnames)
        missing = [
            key for key in (SEG1, schema.seg2_key) if key not in reader.fieldnames
        ]
        if missing:
            raise ProfileError(
                "%s: missing columns: %s" % (path, ", ".join(missing))
            )

        for row in reader:
            row_count += 1
            if row.get("sfn_slot_mismatch", "0") != "0":
                dropped_misaligned += 1
                continue
            if row.get("t0_kernel_real_ns", "1") == "0":
                dropped_missing_kernel += 1
                continue
            try:
                value = float(row[SEG1]) + float(row[schema.seg2_key])
            except (KeyError, TypeError, ValueError):
                dropped_invalid += 1
                continue
            if not math.isfinite(value):
                dropped_invalid += 1
                continue
            values.append(value)

    if not row_count:
        raise ProfileError("%s: no data rows" % path)
    if not values:
        raise ProfileError("%s: no usable epoll timing values" % path)
    return Dataset(
        path,
        tuple(values),
        schema,
        dropped_misaligned,
        dropped_missing_kernel,
        dropped_invalid,
    )


def plot_cdfs(datasets: Sequence[Dataset]) -> None:
    fig, ax = plt.subplots(figsize=(4.33, 2))
    for dataset in datasets:
        ordered = sorted(dataset.values)
        cdf = [(index + 1) / len(ordered) for index in range(len(ordered))]
        ax.step(
            ordered,
            cdf,
            where="post",
            linewidth=2.25,
            label=dataset.path.stem,
        )

    ax.set_xlabel(
        "epoll() processing (us)", fontweight="bold", fontsize=18
    )
    ax.xaxis.label.set_x(0.45)
    ax.set_ylabel("CDF", fontweight="bold", fontsize=18)
    ax.set_xlim(0.0, 1000.0)
    ax.set_ylim(0.0, 1.0)
    ax.tick_params(axis="x", labelsize=14)
    ax.tick_params(axis="y", labelsize=16)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(OUTPUT_PATH, format="pdf", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plot epoll-attributable middlebox latency CDFs from one or more "
            "profiler CSV files."
        )
    )
    parser.add_argument(
        "csv_files",
        metavar="CSV",
        nargs="+",
        type=Path,
        help="profiler CSV written by src/prof.c",
    )
    return parser


def main(argv: Sequence[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        datasets = [load_dataset(path) for path in args.csv_files]
        plot_cdfs(datasets)
    except (OSError, csv.Error, ProfileError) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1

    for dataset in datasets:
        dropped = (
            dataset.dropped_misaligned
            + dataset.dropped_missing_kernel
            + dataset.dropped_invalid
        )
        detail = ""
        if dropped:
            detail = (
                "; %d dropped (%d misaligned, %d without kernel timestamp, "
                "%d invalid)"
                % (
                    dropped,
                    dataset.dropped_misaligned,
                    dataset.dropped_missing_kernel,
                    dataset.dropped_invalid,
                )
            )
        caveat = (
            "; %s" % dataset.schema.caveat if dataset.schema.caveat else ""
        )
        print(
            "%s: %d values; %s%s%s"
            % (
                dataset.path,
                len(dataset.values),
                dataset.schema.description,
                caveat,
                detail,
            )
        )
    print("PDF: %s" % OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    inputs = sys.argv[1:]
    if len(inputs) == 0:
        print("Assuming default CSVs (25 gNB.csv, 250 gNB.csv)")
        inputs = ["25 gNB.csv", "250 gNB.csv"]
    raise SystemExit(main(inputs))
