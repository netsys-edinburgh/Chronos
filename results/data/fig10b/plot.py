import re
import numpy as np

def parse_rtt_log(filepath):
    """Parse lines like: seq=4 rtt=31.51ms ..."""
    pattern = re.compile(r'rtt=([\d.]+)ms')
    rtts = []
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = pattern.search(line)
            if m:
                rtts.append(float(m.group(1)))
    return rtts

azure_chronos = parse_rtt_log("./data/azurechronos/ue-0-dp.log")
azure_emane   = parse_rtt_log("./data/emaneazure/ue-0-dp.log")
ideal_chronos = parse_rtt_log("./data/idealchronos/ue-0-dp.log")
ideal_emane   = parse_rtt_log("./data/idealemane/ue-0-dp.log")

print(f"azure_chronos: n={len(azure_chronos)}, avg={np.mean(azure_chronos):.2f} ms")
print(f"azure_emane:   n={len(azure_emane)},   avg={np.mean(azure_emane):.2f} ms")
print(f"ideal_chronos: n={len(ideal_chronos)}, avg={np.mean(ideal_chronos):.2f} ms")
print(f"ideal_emane:   n={len(ideal_emane)},   avg={np.mean(ideal_emane):.2f} ms")

import matplotlib.pyplot as plt

groups = ["Testbed", "Azure"]
chronos_avgs = [np.mean(ideal_chronos), np.mean(azure_chronos)]
emane_avgs   = [np.mean(ideal_emane),   np.mean(azure_emane)]

x = np.arange(len(groups))
bar_width = 0.35

fig, ax = plt.subplots(figsize=(2.9, 2))
b1 = ax.bar(x - bar_width/2, chronos_avgs, bar_width, label="Chronos", color='red',      edgecolor='black', linewidth=1.5)
b2 = ax.bar(x + bar_width/2, emane_avgs,   bar_width, label="EMANE",   color='steelblue', edgecolor='black', linewidth=1.5)
# ax.bar_label(b1, fmt="%.1f ms", padding=3, fontsize=8)
# ax.bar_label(b2, fmt="%.1f ms", padding=3, fontsize=8)
ax.set_ylabel("Avg RTT (ms)", fontsize=18)
# ax.set_xlabel("Environment", fontsize=18)
# ax.set_title("Average Data Plane RTT\n(Chronos vs. EMANE — Azure vs. Ideal)")
ax.set_xticks(x)
ax.set_xticklabels(groups, fontsize=16)
ax.tick_params(axis='y', labelsize=16)
ax.set_ylim(0, max(chronos_avgs + emane_avgs) * 1.25)
ax.legend(fontsize=14, loc='upper left')
plt.tight_layout()
fig.savefig("fig10b.pdf", dpi=300, bbox_inches="tight")
