"""Figure 4c - virtualised processing time with and without the Supervisor.

chronos.csv and non-chronos.csv are as raw as this repository gets. They are
written by collect_fib_time.py, which runs the `run` binary against a live
testbed - once with time dilation and once without - so there is no earlier
artefact here to regenerate them from and no way to re-collect them offline.
See README.md for the collection procedure.

fib_times_matrix.csv is a leftover from a different run (10 trials per workload
size, undilated) and is not used by the figure.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

for csv_name in ("chronos.csv", "non-chronos.csv"):
    if not os.path.exists(os.path.join(HERE, csv_name)):
        raise SystemExit(f"missing collected data: {csv_name} (see README.md)")

subprocess.run([sys.executable, "plot_fig14.py"], cwd=HERE, check=True)
