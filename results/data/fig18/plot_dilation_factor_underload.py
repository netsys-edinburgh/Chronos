#!/usr/bin/env python3
"""Generate Fig. 18 dilation factor during full-buffer TCP DL traffic."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt


PING_RE = re.compile(
    r"icmp_seq=(?P<sequence>\d+).*?time[=<](?P<time>[\d.,]+)\s*ms",
    re.IGNORECASE,
)
REFERENCE_DELAY_MS = 15.3
FULL_BUFFER_START = 23
FULL_BUFFER_END = 107


def read_dilation_query_data(path: Path) -> tuple[list[int], list[float]]:
    sequences: list[int] = []
    times_ms: list[float] = []
    text = path.read_text(encoding="utf-8", errors="ignore")
    for match in PING_RE.finditer(text):
        sequences.append(int(match.group("sequence")))
        times_ms.append(float(match.group("time").replace(",", ".")))
    if not sequences:
        raise ValueError(f"no dilation query responses found in {path}")
    return sequences, times_ms


def generate(data_path: Path, output: Path) -> None:
    sequences, times_ms = read_dilation_query_data(data_path)
    dilation = [REFERENCE_DELAY_MS / value for value in times_ms]

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(sequences, dilation)
    ax.axvspan(
        FULL_BUFFER_START,
        FULL_BUFFER_END,
        color="blue",
        alpha=0.2,
        label="Full Buffer\nTCP DL Traffic",
    )
    ax.axvline(FULL_BUFFER_START, color="red", linestyle="dotted", linewidth=2)
    ax.axvline(FULL_BUFFER_END, color="blue", linestyle="dotted", linewidth=2)
    ax.set_xlabel("Time (sec)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Dilation Factor", fontsize=14, fontweight="bold")
    ax.tick_params(axis="both", labelsize=12)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")
    ax.legend(fontsize=10)
    fig.tight_layout()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Parsed {len(sequences)} dilation query responses")
    print(f"Wrote {output}")


def parse_args() -> argparse.Namespace:
    figure_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data", type=Path, default=figure_dir / "dilation_query_data"
    )
    parser.add_argument(
        "--output", type=Path, default=figure_dir / "fig18.pdf"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate(args.data, args.output)
