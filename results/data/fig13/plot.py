#!/usr/bin/env python3

from pathlib import Path
import csv
from typing import Dict, List, Set, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "experiment_results_parsed"
NEIGHBORS_FILE = HERE / "cell_neighbors.csv"
RESULTS_DIR = HERE.parents[1] if HERE.parent.name == "data" else None
OUTPUT = (
    RESULTS_DIR / "output" / "fig13.pdf"
    if RESULTS_DIR is not None
    else HERE / "fig13.pdf"
)
UE_COUNT = 960
CELL_COUNT = 960
GRID_ROWS = 20
GRID_COLS = 48
SNAPSHOTS = (0, 300, 600, 899)


def load_cell_index() -> Dict[int, int]:
    """Map zero-based topology cell IDs onto the compact 960-cell grid."""
    valid_cells: Set[int] = set()
    with NEIGHBORS_FILE.open(newline="") as handle:
        for row in csv.DictReader(handle):
            for column in ("CELL", "NEIGHBOR"):
                cell_id = int(row[column])
                if cell_id <= 1000:
                    valid_cells.add(cell_id - 1)

    ordered_cells = sorted(valid_cells)
    if len(ordered_cells) != CELL_COUNT:
        raise ValueError(
            f"Expected {CELL_COUNT} valid cells in {NEIGHBORS_FILE}, "
            f"found {len(ordered_cells)}"
        )
    return {cell_id: index for index, cell_id in enumerate(ordered_cells)}


def load_handover_plans(
    cell_index: Dict[int, int],
) -> Tuple[Dict[int, List[Tuple[int, int]]], int]:
    plans: Dict[int, List[Tuple[int, int]]] = {}
    handover_count = 0

    for ue_dir in DATA_DIR.glob("ue_*"):
        try:
            ue_id = int(ue_dir.name[len("ue_") :])
        except ValueError:
            continue
        plan_file = ue_dir / f"{ue_id}.txt"
        if not plan_file.exists():
            continue

        events: List[Tuple[int, int]] = []
        for line in plan_file.read_text().splitlines():
            fields = [field.strip() for field in line.split(",")]
            if len(fields) < 2:
                continue
            try:
                target_cell, event_second = map(int, fields[:2])
            except ValueError:
                continue
            if 0 < event_second < 900:
                if target_cell not in cell_index:
                    raise ValueError(f"Cell {target_cell} in {plan_file} is not in the topology")
                events.append((event_second, cell_index[target_cell]))
                handover_count += 1
        plans[ue_id] = sorted(events)

    if not plans:
        raise FileNotFoundError(f"No UE handover plans found in {DATA_DIR}")
    return plans, handover_count


def serving_cell(ue_id: int, events: List[Tuple[int, int]], snapshot: int) -> int:
    cell = ue_id
    for event_second, target_cell in events:
        # Preserve the original figure's convention: an event at exactly the
        # snapshot time is reflected immediately after that snapshot.
        if event_second >= snapshot:
            break
        cell = target_cell
    return cell


def occupancy_at(
    plans: Dict[int, List[Tuple[int, int]]], snapshot: int
) -> np.ndarray:
    occupancy = np.zeros(CELL_COUNT, dtype=int)
    for ue_id in range(UE_COUNT):
        cell = serving_cell(ue_id, plans.get(ue_id, []), snapshot)
        occupancy[cell] += 1
    return occupancy.reshape(GRID_ROWS, GRID_COLS)


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    cell_index = load_cell_index()
    plans, handover_count = load_handover_plans(cell_index)
    heatmaps = {snapshot: occupancy_at(plans, snapshot) for snapshot in SNAPSHOTS}
    values = np.concatenate([matrix.ravel() for matrix in heatmaps.values()])

    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    image = None
    for index, snapshot in enumerate(SNAPSHOTS):
        image = axes[index].imshow(
            heatmaps[snapshot],
            aspect="auto",
            vmin=values.min(),
            vmax=values.max(),
            cmap="plasma",
        )
        axes[index].set_title(f"t = {snapshot}s", fontsize=24, fontweight="bold")
        axes[index].tick_params(labelsize=12)

    fig.subplots_adjust(bottom=0.25)
    colorbar_axis = fig.add_axes([0.15, 0.05, 0.7, 0.05])
    colorbar = fig.colorbar(image, cax=colorbar_axis, orientation="horizontal")
    colorbar.set_label("UE count", fontsize=24, fontweight="bold")
    colorbar.ax.tick_params(labelsize=12)
    for label in colorbar.ax.get_xticklabels():
        label.set_fontweight("bold")

    fig.savefig(OUTPUT, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)

    print(f"Read {len(plans)} observed UE handover plans")
    print(f"Recorded handovers: {handover_count}")
    print(f"UEs represented at each snapshot: {[int(m.sum()) for m in heatmaps.values()]}")
    print(f"t=0 occupancy range: {heatmaps[0].min()}-{heatmaps[0].max()}")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
