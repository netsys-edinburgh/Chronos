#!/usr/bin/env python3
"""Generate the Fig. 8 average-ping bar chart from raw ping logs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


PING_TIME_RE = re.compile(r"\btime[=<](?P<time>[\d.,]+)\s*ms\b", re.IGNORECASE)


def read_ping_times(path: Path) -> list[float]:
    """Return all successful ping response times in milliseconds from *path*."""
    times = [
        float(match.group("time").replace(",", "."))
        for match in PING_TIME_RE.finditer(
            path.read_text(encoding="utf-8", errors="ignore")
        )
    ]
    if not times:
        raise ValueError(f"no ping response times found in {path}")
    return times


def mean_ping(path: Path) -> float:
    return float(np.mean(read_ping_times(path)))


def plot_ping_averages(data_dir: Path, output: Path) -> None:
    chronos = [mean_ping(data_dir / "chronos_0"), mean_ping(data_dir / "chronos_3")]
    cots = [mean_ping(data_dir / "cots_0"), mean_ping(data_dir / "cots_3")]

    positions = np.arange(2)
    width = 0.35

    fig, ax = plt.subplots(figsize=(3, 2))
    ax.bar(
        positions - width / 2,
        chronos,
        width,
        label="Chronos",
        color="red",
        edgecolor="black",
        linewidth=1.5,
    )
    ax.bar(
        positions + width / 2,
        cots,
        width,
        label="COTS",
        color="green",
        edgecolor="black",
        linewidth=1.5,
    )

    ax.set_ylabel("Avg Ping\n (ms)", fontsize=18)
    # Keep the second (blank) line used by the original figure's layout.
    ax.set_xticks(positions, ["conf#1\n", "conf#2\n"], fontsize=13)
    ax.set_yticks([0, 50])
    ax.tick_params(axis="y", labelsize=16)
    ax.set_ylim(0, 51.5)
    ax.legend(loc="upper left", fontsize=14, framealpha=0.8)

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)

    print(f"Chronos averages: conf#1={chronos[0]:.3f} ms, conf#2={chronos[1]:.3f} ms")
    print(f"COTS averages:    conf#1={cots[0]:.3f} ms, conf#2={cots[1]:.3f} ms")
    print(f"Wrote {output}")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=script_dir / "data",
        help="directory containing chronos_0, chronos_3, cots_0, and cots_3",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "fig8a.pdf",
        help="output figure path (default: fig8a.pdf)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    plot_ping_averages(args.data_dir, args.output)
