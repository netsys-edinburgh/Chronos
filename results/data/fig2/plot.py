"""Figure 2 - CDFs of compute interruption and network latency across cloud providers.

Both panels are drawn from raw measurement logs held here: osnoise/*.log is
cyclictest output, ping/*.ping.log is ping output. All parsing happens inside
gen_latencies_cdf.py, which globs those directories relative to itself, so it is
run with cwd set here.

Files ending .exclude are deliberately not picked up by the glob - they are runs
the authors chose to leave out.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

subprocess.run([sys.executable, "gen_latencies_cdf.py"], cwd=HERE, check=True)
