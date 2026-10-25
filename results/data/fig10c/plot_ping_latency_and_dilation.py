import os
import re
import numpy as np
import matplotlib.pyplot as plt

def parse_ping_latency(ue_log_path):
    """Parse all RTT values from ue-0-dp.log and return the average and std."""
    rtt_values = []
    with open(ue_log_path, 'r') as f:
        for line in f:
            m = re.search(r'rtt=([\d\.]+)ms', line)
            if m:
                rtt_values.append(float(m.group(1)))
    if rtt_values:
        return np.mean(rtt_values), np.std(rtt_values)
    else:
        return None, None

def parse_dilation(globalsc_log_path, last_n=10):
    """Parse the last N lines of globalsc.log for Dilation factor and return the average."""
    dilation_values = []
    with open(globalsc_log_path, 'r') as f:
        lines = f.readlines()[-last_n:]
        for line in lines:
            m = re.search(r'Dilation factor: ([\d\.]+)', line)
            if m:
                dilation_values.append(float(m.group(1)))
    if dilation_values:
        return np.mean(dilation_values)
    else:
        return None

def collect_data(base_dir='.'):
    """Collect (preempt, avg_ping_latency, std_ping_latency, avg_dilation) for all subdirs."""
    data = []
    preempts = ["0", "25000", "30000", "35000", "40000", "45000", "50000", "100000", "500000"]
    preempts = ["0", "30000", "40000", "50000", "100000", "500000"]
    for preempt in preempts:
        ue_log = f"logs/ue-{preempt}.log"
        globalsc_log = f"logs/globalsc-{preempt}.log"
        if os.path.isfile(ue_log) and os.path.isfile(globalsc_log):
            avg_ping, std_ping = parse_ping_latency(ue_log)
            avg_dilation = parse_dilation(globalsc_log)
            if avg_ping is not None and avg_dilation is not None:
                data.append((preempt, avg_ping, std_ping, avg_dilation))
    return data

def plot_dual_axis(data):
    preempts, pings, stds, dilations = zip(*data)
    fig, ax1 = plt.subplots(figsize=(3,2))

    color1 = 'tab:blue'
    ax1.set_xlabel('Preempt Size (10k CPU Ops)              ', fontweight='bold', fontsize=13)
    ax1.set_ylabel('UE ping\nRTT (ms)', color=color1, fontweight='bold', fontsize=18)
    ax1.errorbar(preempts, pings, yerr=stds, marker='o', color=color1, label='UE Ping Latency', linestyle='-', capsize=4)
    ax1.tick_params(axis='y', labelcolor=color1, labelsize=16)
    ax1.tick_params(axis='x', labelsize=12)
    for label in ax1.get_xticklabels():
        label.set_fontweight('bold')
    for label in ax1.get_yticklabels():
        label.set_fontweight('bold')
    ax1.set_ylim(0, 35) # matches other figure
    ax1.set_xticks(preempts, ["0", "3", "4", "5", "10", "50"])

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color2 = 'tab:red'
    ax2.set_yticks([])
    ax1.set_yticks([0, 20])
    #ax2.set_ylabel('Dilation Factor', color=color2, fontweight='bold', fontsize=18)
    ax2.plot(preempts, dilations, marker='s', color=color2, label='Dilation Factor', linestyle='--')
    ax2.tick_params(axis='y', labelcolor=color2, labelsize=16)
    for label in ax2.get_yticklabels():
        label.set_fontweight('bold')
    ax2.set_ylim(0, 27) # matches other figure

    fig.tight_layout()
    # plt.title("Average UE ping latency (left axis) and Dilation factor (right axis)\nvs. Size of Network Latencies")  # 已去除标题
    plt.savefig('fig10c.pdf', dpi=300)

if __name__ == "__main__":
    data = collect_data('.')
    if not data:
        print("No data found! Make sure to run this script in the parent directory of the latency folders.")
    else:
        plot_dual_axis(data)
