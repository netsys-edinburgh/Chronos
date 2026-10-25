#!/usr/bin/env python3
"""Generate Figure 15(b), the standalone slot-completion-time CDF panel."""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def parse_slot_times(path):
    """Read the slot-completion-time samples in microseconds."""
    samples = np.loadtxt(path, dtype=int, ndmin=1)
    if samples.size == 0:
        raise ValueError(f"No slot-completion-time samples found in {path}")
    return samples


def ecdf(samples):
    x = np.sort(samples)
    y = np.arange(1, len(x) + 1) / len(x)
    return x, y


def main():
    here = Path(__file__).resolve().parent
    # The original combined notebook kept the slot-time samples beside fig15a.
    data_dir = here.parent / "fig15a"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=here / "fig15b.pdf")
    args = parser.parse_args()

    traces = [
        ("nc_connnect", "Idle", "#c47d00"),
        ("nc_ping", "Ping", "#b52828"),
        ("nc_iperfdl", "Iperf DL", "#9467bd"),
        ("nc_iperful", "Iperf UL", "#8c564b"),
        ("c_connect", "Chronos-Idle", "#1a6fbd"),
        ("c_ping", "Chronos-Ping", "#17becf"),
        ("c_iperfdl", "Chronos-Iperf DL", "#1e8f4e"),
        ("c_iperful", "Chronos-Iperf UL", "#e377c2"),
    ]

    font_size = 13
    fig, ax = plt.subplots(figsize=(4.87, 3.84))
    fig.subplots_adjust(left=0.19, right=0.93, bottom=0.50, top=0.96)
    for filename, label, color in traces:
        x, y = ecdf(parse_slot_times(data_dir / filename))
        ax.plot(x, y, color=color, linewidth=2.5, label=label)

    ax.set_xlabel("Slot Completion Time (µs)", fontsize=16, fontweight="bold")
    ax.set_ylabel("CDF", fontsize=16, fontweight="bold")
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 5000)
    ax.tick_params(labelsize=14)
    plt.setp(ax.get_xticklabels(), fontweight="bold")
    plt.setp(ax.get_yticklabels(), fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend(
        fontsize=font_size,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.34),
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
