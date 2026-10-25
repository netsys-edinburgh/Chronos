#!/usr/bin/env python3
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "fig4b.pdf")

CATEGORIES = ["PHY bypass", "Full PHY"]
CPU = [0.307, 3.135]
THROUGHPUT = [0.003, 9.880]

CPU_COLOR = "#1f77b4"
NET_COLOR = "red"

plt.rcParams.update({
    "font.size": 12,
    "font.weight": "bold",
    "axes.labelweight": "bold",
})

fig, ax1 = plt.subplots(figsize=(4.5, 3))
ax2 = ax1.twinx()

x = np.arange(len(CATEGORIES)) * 1.5
width = 0.35

b1 = ax1.bar(x - width / 2, CPU, width, color=CPU_COLOR, label="CPU (cores)")
b2 = ax2.bar(x + width / 2, THROUGHPUT, width, color=NET_COLOR,
             label="Throughput (Gbit/s)")

ax1.set_ylabel("CPU (cores)", color=CPU_COLOR, fontweight="bold")
ax1.set_ylim(0, 5.5)
ax1.set_yticks(np.arange(0, 5.1, 1))
ax1.tick_params(axis="y", colors=CPU_COLOR, labelsize=13)
for label in ax1.get_yticklabels():
    label.set_fontweight("bold")

ax2.set_ylabel("Throughput (Gbit/s)", color=NET_COLOR, fontweight="bold")
ax2.set_ylim(0, 12)
ax2.set_yticks(np.arange(0, 12.1, 2))
ax2.tick_params(axis="y", colors=NET_COLOR, labelsize=13)
for label in ax2.get_yticklabels():
    label.set_fontweight("bold")

ax1.set_xticks(x)
ax1.set_xticklabels(CATEGORIES, fontsize=15, fontweight="bold")

for rect, val in zip(b1, CPU):
    ax1.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 0.12,
              f"{val:.3f}", ha="center", va="bottom", color=CPU_COLOR,
              fontsize=11, fontweight="bold")
for rect, val in zip(b2, THROUGHPUT):
    ax2.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 0.25,
              f"{val:.3f}", ha="center", va="bottom", color=NET_COLOR,
              fontsize=11, fontweight="bold")

ax1.legend([b1, b2], ["CPU (cores)", "Throughput (Gbit/s)"],
           loc="upper left", fontsize=12, frameon=False)

fig.tight_layout()
fig.text(0.01, 0.01, "(b)", ha="left", va="bottom",
         fontsize=10, fontweight="bold")
fig.savefig(OUT)
print("wrote", OUT)
