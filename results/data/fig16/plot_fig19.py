import os
import glob
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def parse_dilation_from_log(logfile, last_n=10):
    """Parse last n lines of logfile for dilation factors, return their mean."""
    dilation_factors = []
    with open(logfile, 'r') as f:
        lines = f.readlines()[-last_n:]
        for line in lines:
            m = re.search(r'Dilation factor: ([\d\.]+)', line)
            if m:
                dilation_factors.append(float(m.group(1)))
    if dilation_factors:
        return np.mean(dilation_factors)
    else:
        return None

def collect_data(log_pattern='globalsc_*.log'):
    data = []
    for fname in glob.glob(log_pattern):
        m = re.match(r'globalsc_(\d+)\.log', os.path.basename(fname))
        if m:
            nodes = int(m.group(1))
            mean_dilation = parse_dilation_from_log(fname)
            if mean_dilation is not None:
                data.append((nodes, mean_dilation))
    data.sort()
    return data

def plot(data):
    nodes, dilations = zip(*data)
    plt.figure(figsize=(6,3))
    plt.plot(nodes, dilations, marker='o', linestyle='-', color='blue')
    plt.ylim(0, 10)
    plt.xlabel('Number of Cloud Instances', fontsize=18, fontweight='bold')
    plt.ylabel('Dilation Factor', fontsize=18, fontweight='bold')
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=16)
    # Set tick labels bold
    ax = plt.gca()
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
        label.set_fontsize(16)
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
        label.set_fontsize(16)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()
    plt.savefig('fig16.pdf', dpi=300)

if __name__ == "__main__":
    data = collect_data()
    if not data:
        print("No log files found or no data parsed!")
    else:
        plot(data)
