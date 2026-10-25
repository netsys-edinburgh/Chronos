"""Figure 10d - dilation factor and ping latency under injected network latency.

Unlike fig10c there is no extraction step: logs/ holds the raw per-latency
globalsc and UE logs exactly as the experiment wrote them.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

subprocess.run([sys.executable, "plot_ping_latency_and_dilation.py"], cwd=HERE, check=True)
