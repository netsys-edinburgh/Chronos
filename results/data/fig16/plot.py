"""Figure 15 (appendix) - dilation factor as the number of cloud instances grows.

globalsc_<N>.log is the raw output of a run with N Slot Monitors; the parsing
happens inside plot_fig19.py. Run with cwd set to this directory so its relative
globalsc_*.log glob resolves regardless of where the caller is.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

subprocess.run([sys.executable, "plot_fig19.py"], cwd=HERE, check=True)
