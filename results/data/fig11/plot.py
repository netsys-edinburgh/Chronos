#!/usr/bin/env python3

from pathlib import Path
from typing import Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "experiment_results_parsed"
RESULTS_DIR = HERE.parents[1] if HERE.parent.name == "data" else None
OUTPUT = (
    RESULTS_DIR / "output" / "fig11.pdf"
    if RESULTS_DIR is not None
    else HERE / "fig11.pdf"
)
MINUTES = range(15)


def load_messages() -> Tuple[pd.DataFrame, int]:
    files = sorted(DATA_DIR.glob("ue_*/messages_per_min.csv"))
    if not files:
        raise FileNotFoundError(f"No messages_per_min.csv files found in {DATA_DIR}")

    rows = pd.concat((pd.read_csv(path) for path in files), ignore_index=True)
    rows["minute"] = pd.to_numeric(rows["minute"], errors="coerce")
    for column in ("x2ap", "s1ap", "rrc"):
        rows[column] = pd.to_numeric(rows[column], errors="coerce").fillna(0)

    totals = (
        rows.dropna(subset=["minute"])
        .groupby("minute")[["x2ap", "s1ap", "rrc"]]
        .sum()
        .reindex(MINUTES, fill_value=0)
    )
    return totals, len(files)


def main() -> None:
    totals, ue_count = load_messages()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    x2ap = totals["x2ap"]
    s1ap = totals["s1ap"]
    rrc = totals["rrc"]

    minutes = np.arange(15)
    y1 = rrc.to_numpy()
    y2 = (rrc + x2ap).to_numpy()
    y3 = (rrc + x2ap + s1ap).to_numpy()

    yticks = np.arange(0, 2001, 250)

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.fill_between(minutes, 0, y1, alpha=0.9, label="RRC")
    ax.fill_between(minutes, y1, y2, alpha=0.6, label="X2AP")
    ax.fill_between(minutes, y2, y3, alpha=0.4, label="S1AP")
    ax.plot(minutes, y3, linewidth=1)
    ax.set_xlabel("Time(minutes)", fontweight="bold", fontsize=12)
    ax.set_ylabel("Mobility Signaling \n Messages \n ", fontweight="bold", fontsize=12)
    ax.set_xticks(minutes)
    ax.set_yticks(yticks)
    ax.set_ylim(0, 2000)
    ax.tick_params(left=True, labelleft=True, bottom=True, labelbottom=True, labelsize=12)
    ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=12)
    fig.tight_layout()
    fig.savefig(OUTPUT, bbox_inches="tight", dpi=300)
    plt.close(fig)

    protocol_totals = {name: int(totals[name].sum()) for name in ("x2ap", "s1ap", "rrc")}
    print(f"Read {ue_count} observed UE result folders")
    print(f"Messages in minutes 0-14: {sum(protocol_totals.values())}")
    print(f"Protocol totals: {protocol_totals}")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
