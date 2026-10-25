import os
import re
import numpy as np
import matplotlib.pyplot as plt

def parse_rtt(line):
    """
    Parse RTT value from a line, convert to ms if needed.
    Returns float value in ms or None if not found.
    """
    m = re.search(r'rtt=([\d\.]+)(ms|s)', line)
    if m:
        val = float(m.group(1))
        unit = m.group(2)
        if unit == 's':
            return val * 1000
        else:
            return val
    return None

def parse_ue_dp_log(log_path):
    """
    Parse all RTTs from a single ue-*-dp.log file, return all RTT values in ms.
    """
    rtts = []
    with open(log_path, 'r') as f:
        for line in f:
            val = parse_rtt(line)
            if val is not None:
                rtts.append(val)
    return rtts

def collect_ue_stats(base_dir):
    """
    For each experiment directory, collect all RTTs from all ue-*-dp.log files,
    and compute the mean and std of all RTTs. Return a list of (n_ues, avg, std).
    """
    stats = []
    # Only consider directories whose names start with an integer
    for d in os.listdir(base_dir):
        d_path = os.path.join(base_dir, d)
        m = re.match(r'^(\d+)_', d)
        if os.path.isdir(d_path) and m:
            attempted_ues = int(m.group(1))
            rtts_all = []
            # Find all ue-*-dp.log in this directory
            active_ues = 0
            for fname in os.listdir(d_path):
                if re.match(r'^ue-\d+-dp\.log$', fname):
                    rtts = parse_ue_dp_log(os.path.join(d_path, fname))
                    if len(rtts) > 0:
                        active_ues += 1
                    rtts_all.extend(rtts)
            if rtts_all:
                avg = np.mean(rtts_all)
                std = np.std(rtts_all)
                stats.append((attempted_ues, active_ues, avg, std))
                print(f"{os.path.basename(base_dir):>8} | Attempted UEs: {attempted_ues:4d} | Active UEs: {active_ues:4d} | AVG ping latency: {avg:8.2f} ms | STD: {std:8.2f} ms | Samples: {len(rtts_all)}")
    # Sort by n_ues
    stats.sort(key=lambda x: x[0])
    return stats

def plot_ue_stats(stats, label, marker, color, linestyle):
    if stats:
        attempted_ues, active_ues, avgs, stds = zip(*stats)
        ratio = [100*a/b for a,b in zip(active_ues, attempted_ues)]
        plt.plot(attempted_ues, ratio, color=color, markersize=10, linewidth=2, label=label, linestyle=linestyle)
    else:
        print(f"No valid data for {label}")

def main():
    print(f"Current working directory: {os.getcwd()}")
    # Use new data directories under ../LargeScale
    dirs = [("../LargeScale/EMANE", "x", "blue"), ("../LargeScale/Chronos", "o", "tab:orange")]
    plt.figure(figsize=(3.5,3 ))

    for dirname, marker, color in dirs:
        if os.path.isdir(dirname):
            stats = collect_ue_stats(dirname)
            plot_ue_stats(stats, label='Chronos' if os.path.basename(dirname) == 'Chronos' else 'EMANE', marker=marker, color=color, linestyle='--')
        else:
            print(f"Directory '{dirname}' not found. Skipping.")

    plt.xscale('log')
    plt.yscale('log')
    plt.xlabel('Scale (#UE/#gNB)', fontweight='bold', fontsize=18)
    plt.ylabel('Data Plane Success (%))     ', fontweight='bold', fontsize=16)
    # Remove title
    # plt.title('Average UE ping vs #UEs in experiment')
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.legend(fontsize=9)
    plt.tight_layout()
    # Add some space to the right of x-axis (beyond 100)
    plt.xlim(0, 12000)
    plt.xticks([1,10,100,1000,10000], ["1","10","100","1k","10k"])
    plt.yticks([50, 60, 70, 80, 90, 100], [50, 60, 70, 80, 90, 100])
    # Make x and y axis tick labels bold and larger
    ax = plt.gca()
    for label in ax.get_xticklabels():
        label.set_fontweight('bold')
        label.set_fontsize(16)
    for label in ax.get_yticklabels():
        label.set_fontweight('bold')
        label.set_fontsize(16)
    plt.tight_layout()
    plt.savefig('fig9b.pdf', dpi=300)

if __name__ == "__main__":
    main()
