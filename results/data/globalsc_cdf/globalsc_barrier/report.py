from __future__ import annotations

import csv
from collections.abc import Sequence
from pathlib import Path

from globalsc_barrier.model import ArrivalRow


CSV_FIELDS = [
    "round_index",
    "slot",
    "role",
    "participant_id",
    "arrival_offset_ms",
]


class MatplotlibUnavailableError(Exception):
    """Raised when matplotlib cannot be imported for mandatory PDF output."""


def write_csv(path: Path, arrivals: Sequence[ArrivalRow]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(CSV_FIELDS)
        for row in arrivals:
            writer.writerow(
                [
                    row.round_index,
                    row.slot,
                    row.role,
                    row.participant_id,
                    f"{row.arrival_offset_ms:.6f}",
                ]
            )


def write_pdf_cdf(path: Path, arrivals: Sequence[ArrivalRow]) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise MatplotlibUnavailableError("matplotlib is required to write the PDF CDF") from error

    values = sorted(row.arrival_offset_ms for row in arrivals)
    y_values = [(index + 1) / len(values) for index in range(len(values))] if values else []
    fig, ax = plt.subplots()
    ax.plot(values, y_values, marker=".")
    ax.set_xlabel("Barrier arrival offset from slot issue (ms)")
    ax.set_ylabel("CDF")
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(path, format="pdf")
    plt.close(fig)
