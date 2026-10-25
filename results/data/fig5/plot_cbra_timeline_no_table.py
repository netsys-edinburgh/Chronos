#!/usr/bin/env python3
"""Generate the three-row Fig. 5 CBRA timeline without the data table."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt


@dataclass(frozen=True)
class Event:
    number: int
    slot: int
    source: str
    destination: str


# Colors recovered from the reference PDF.
ARROW_COLORS = ("#1a6fbd", "#c47d00", "#1e8f4e", "#b52828")


def read_events(csv_path: Path) -> tuple[list[Event], list[Event], list[Event]]:
    """Read all Testbed, Chronos, and NS3 event slots from the figure CSV."""
    testbed: list[Event] = []
    chronos: list[Event] = []
    ns3: list[Event] = []

    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            direction = row["Direction"].strip()
            if "→" not in direction:
                raise ValueError(f"invalid direction {direction!r} in {csv_path}")
            source, destination = (part.strip() for part in direction.split("→", 1))
            number = int(row["#"])
            testbed.append(
                Event(number, int(row["# Slot \n Testbed"]), source, destination)
            )
            chronos.append(
                Event(number, int(row["# Slot \n Chronos"]), source, destination)
            )
            ns3_slot = row["# Slot \n NS3"].strip()
            if ns3_slot.lower() != "skipped":
                ns3.append(Event(number, int(ns3_slot), source, destination))

    if len(testbed) != 4 or len(chronos) != 4 or len(ns3) != 3:
        raise ValueError(
            f"expected 4 Testbed, 4 Chronos, and 3 NS3 events in {csv_path}; "
            f"found {len(testbed)}, {len(chronos)}, and {len(ns3)}"
        )
    return testbed, chronos, ns3


def plot_timeline(
    ax: plt.Axes,
    events: list[Event],
    name: str,
    *,
    skipped_msg4: bool = False,
) -> None:
    y_pos = {"UE": 1.0, "gNB": 0.5}
    last_slot = 26

    ax.hlines(
        [y_pos["UE"], y_pos["gNB"]],
        xmin=-0.5,
        xmax=last_slot + 1,
        color="tab:blue",
        linewidth=2,
    )
    ax.text(-0.45, 1.2, "UE", ha="left", va="center", fontsize=12, fontweight="bold")
    ax.text(-0.45, -0.2, "gNB", ha="left", va="center", fontsize=12, fontweight="bold")

    tilt = 0.6
    for event, color in zip(events, ARROW_COLORS):
        y0 = y_pos[event.source]
        y1 = y_pos[event.destination]
        ax.annotate(
            "",
            xy=(event.slot + tilt, y1),
            xytext=(event.slot - tilt, y0),
            arrowprops={"arrowstyle": "->", "color": color, "linewidth": 2},
            annotation_clip=False,
        )
        ax.text(
            event.slot,
            (y0 + y1) / 6,
            f"msg{event.number}",
            color="white",
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            bbox={"boxstyle": "square,pad=0.25", "fc": "black", "ec": color, "lw": 1.5},
        )
        ax.text(
            event.slot + tilt + 1,
            y1 + 0.3,
            f"t={event.slot}",
            ha="center",
            va="top",
            fontsize=10,
            fontweight="bold",
        )

    if skipped_msg4:
        ax.text(
            24,
            0.75,
            "Msg4: Skipped",
            color="red",
            fontsize=12,
            fontweight="bold",
            ha="center",
            va="center",
            bbox={
                "boxstyle": "round,pad=0.35",
                "facecolor": "#ffe4e1",
                "edgecolor": "red",
                "linestyle": "--",
            },
        )
    else:
        msg3_slot = next(event.slot for event in events if event.number == 3)
        ax.axvspan(msg3_slot, msg3_slot + 7, 0.5, 0.75, alpha=0.15)
        ax.text(
            msg3_slot,
            1.25,
            r"$\Delta$ > 7 for Msg3",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title(f"NR CBRA RACH Timeline - {name}", fontsize=13, fontweight="bold", pad=6)
    ax.set_xlim(-0.5, last_slot + 1)
    ax.set_ylim(-0.5, 1.5)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def generate(csv_path: Path, output: Path) -> None:
    testbed, chronos, ns3 = read_events(csv_path)

    fig, axes = plt.subplots(3, 1, figsize=(8, 3))
    plot_timeline(axes[0], testbed, "Testbed")
    plot_timeline(axes[1], chronos, "Chronos")
    plot_timeline(axes[2], ns3, "NS3", skipped_msg4=True)

    # Match the reference PDF's 558 × 68.376 pt stacked plotting areas.
    fig.subplots_adjust(
        left=0.025,
        right=0.99375,
        bottom=0.025,
        top=0.9746666667,
        hspace=0,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {output}")


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=script_dir / "cbra_timeline.csv")
    parser.add_argument(
        "--output", type=Path, default=script_dir / "fig5.pdf"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate(args.csv, args.output)
