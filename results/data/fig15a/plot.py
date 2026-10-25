#!/usr/bin/env python3
"""Generate Figure 15(a), the standalone throughput time-series panel."""

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


IPERF_INTERVAL = re.compile(
    r"\d+\.\d+-\s*\d+\.\d+\s+sec.*?([\d.]+)\s+Mbits/sec"
)


def parse_iperf(path):
    """Extract per-second throughput samples in Mbits/s from an iperf3 log."""
    samples = []
    for line in path.read_text(errors="ignore").splitlines():
        match = IPERF_INTERVAL.search(line)
        if match:
            samples.append(float(match.group(1)))
    if not samples:
        raise ValueError(f"No interval throughput samples found in {path}")
    return np.asarray(samples)


def main():
    here = Path(__file__).resolve().parent
    # The original combined notebook kept the throughput logs beside fig15b.
    data_dir = here.parent / "fig15b"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=here / "fig15a.pdf")
    args = parser.parse_args()

    traces = [
        (parse_iperf(data_dir / "iperf3_c_dl")[:88], "Chronos DL", "#1a6fbd"),
        (parse_iperf(data_dir / "iperf3_c_ul")[:88], "Chronos UL", "#1e8f4e"),
        (parse_iperf(data_dir / "iperf_nc_dl")[:88], "Native DL", "#c47d00"),
        (parse_iperf(data_dir / "iperf3_nc_ul")[:88], "Native UL", "#b52828"),
    ]

    font_size = 13
    fig, ax = plt.subplots(figsize=(4.87, 3.84))
    fig.subplots_adjust(left=0.19, right=0.96, bottom=0.32, top=0.96)
    for samples, label, color in traces:
        ax.plot(samples, color=color, alpha=0.85, linewidth=2.5, label=label)
        ax.axhline(
            samples.mean(), color=color, linestyle="--", linewidth=2, alpha=0.7
        )

    ax.set_xlabel("Time (s)", fontsize=16, fontweight="bold")
    ax.set_ylabel("Throughput (Mbits/s)", fontsize=16, fontweight="bold")
    ax.tick_params(labelsize=14)
    plt.setp(ax.get_xticklabels(), fontweight="bold")
    plt.setp(ax.get_yticklabels(), fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(
        fontsize=font_size,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.17),
        bbox_transform=fig.transFigure,
        ncol=2,
        prop={"weight": "bold", "size": font_size},
        frameon=True,
        borderaxespad=0,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output)
    plt.close(fig)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
