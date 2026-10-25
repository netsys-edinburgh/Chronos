#!/usr/bin/env python3
"""Generate the combined Fig. 6 throughput bar and time-series panels."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


IPERF_INTERVAL_RE = re.compile(
    r"\[\s*\d+\s*\]\s*"
    r"[\d.]+\s*-\s*[\d.]+\s*sec\s+.*?"
    r"(?P<value>[\d.]+)\s*(?P<unit>[KMG]?bits/sec|[KMG]?bit/s)",
    re.IGNORECASE,
)

UNIT_TO_MBPS = {
    "bit/s": 1e-6,
    "bits/sec": 1e-6,
    "kbit/s": 1e-3,
    "kbits/sec": 1e-3,
    "mbit/s": 1.0,
    "mbits/sec": 1.0,
    "gbit/s": 1e3,
    "gbits/sec": 1e3,
}


def read_published_bars(notebook: Path) -> tuple[dict[str, float], dict[str, float]]:
    """Read the published COTS and Chronos dictionaries from the Fig. 6a notebook."""
    document = json.loads(notebook.read_text(encoding="utf-8"))
    values: dict[str, dict[str, float]] = {}

    for cell in document.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                continue
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in {"cots", "chronos"}:
                parsed = ast.literal_eval(node.value)
                values[target.id] = {str(key): float(value) for key, value in parsed.items()}

    if "cots" not in values or "chronos" not in values:
        raise ValueError(f"could not find cots and chronos throughput dictionaries in {notebook}")
    if list(values["cots"]) != list(values["chronos"]):
        raise ValueError("COTS and Chronos traffic categories do not match")
    return values["cots"], values["chronos"]


def read_iperf_intervals(path: Path) -> list[float]:
    """Parse per-interval iperf throughput values and normalize them to Mbit/s."""
    values: list[float] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        lowered = line.lower()
        if "sender" in lowered or "receiver" in lowered:
            continue
        match = IPERF_INTERVAL_RE.search(line)
        if match:
            values.append(
                float(match.group("value")) * UNIT_TO_MBPS[match.group("unit").lower()]
            )
    if not values:
        raise ValueError(f"no iperf intervals found in {path}")
    return values


def generate(fig6a_dir: Path, fig6b_dir: Path, output: Path) -> None:
    cots_bars, chronos_bars = read_published_bars(fig6a_dir / "plot_fig6.ipynb")
    cots_trace = read_iperf_intervals(fig6b_dir / "cots.log")
    chronos_trace = read_iperf_intervals(fig6b_dir / "chronos.log")

    labels = list(cots_bars)
    positions = np.arange(len(labels))
    width = 0.35
    cots_color = "tab:blue"
    chronos_color = "tab:orange"

    fig, (bars_ax, trace_ax) = plt.subplots(1, 2, figsize=(12, 3))

    bars_ax.bar(
        positions - width / 2,
        list(cots_bars.values()),
        width,
        color=cots_color,
        edgecolor="black",
        linewidth=1.5,
        label="COTS",
    )
    bars_ax.bar(
        positions + width / 2,
        list(chronos_bars.values()),
        width,
        color=chronos_color,
        edgecolor="black",
        linewidth=1.5,
        label="Chronos",
    )
    bars_ax.set_xticks(positions, labels, fontsize=16)
    bars_ax.set_yticks([0, 10, 20, 30])
    bars_ax.tick_params(axis="y", labelsize=16)
    bars_ax.set_ylim(0, 37.8)
    bars_ax.set_xlabel("Traffic Type\n (a)", fontsize=18)
    bars_ax.set_ylabel("Throughput\n (Mbps)", fontsize=18)

    trace_ax.plot(cots_trace, color=cots_color, linewidth=2.5, label="COTS")
    trace_ax.plot(chronos_trace, color=chronos_color, linewidth=2.5, label="Chronos")
    trace_ax.set_xlabel("Time Interval (s)\n (b)", fontsize=18)
    trace_ax.set_xticks([0, 10, 20, 30])
    trace_ax.set_yticks([2, 4, 6, 8])
    trace_ax.tick_params(axis="both", labelsize=16)
    trace_ax.grid(True)

    handles, legend_labels = bars_ax.get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.07938368),
        ncol=2,
        fontsize=14,
        framealpha=1,
    )
    fig.tight_layout()

    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Bar data: COTS={list(cots_bars.values())}, Chronos={list(chronos_bars.values())}")
    print(f"Trace data: COTS={len(cots_trace)} points, Chronos={len(chronos_trace)} points")
    print(f"Wrote {output}")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fig6a-dir", type=Path, default=script_dir / "source_data" / "fig6a")
    parser.add_argument("--fig6b-dir", type=Path, default=script_dir / "source_data" / "fig6b")
    parser.add_argument(
        "--output", type=Path, default=script_dir / "fig6.pdf"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate(args.fig6a_dir, args.fig6b_dir, args.output)
