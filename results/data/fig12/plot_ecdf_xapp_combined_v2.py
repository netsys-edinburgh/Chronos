#!/usr/bin/env python3
"""Combined figure for usecase.tex "Data for AI/ML based RAN Apps", v2:
(left) pooled ECDF of per-UE UL RB grants across cell-load tiers (unchanged
from v1), (right) closed-loop xApp A-B-A OLLA target-BLER sweep, now with
3dB DL HARQ gain applied (EMURAN_DL_HARQ_GAIN_DB=3, matching the paper's
documented 18dB SINR / 3dB HARQ gain methodology). Panel (c) now shows
mean cwnd in place of RTT; (b) MCS and (d) goodput unchanged in kind.

Data: local ECDF data and captured 18dB SINR, 150s runs:
  A  = bler005_18db_150s_hg3_r2  (target 0.05)
  B  = bler020_18db_150s_hg3     (target 0.20)
  A' = bler005_18db_150s_hg3_r3b (target 0.05)
Output: fig12.pdf in this script's directory.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "fig12.pdf")
ECDF_DATA = os.path.join(ROOT, "ecdf", "ul_ecdf_steps.json")

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 12,
    "axes.labelsize": 13, "xtick.labelsize": 12, "ytick.labelsize": 12,
    "font.weight": "bold", "axes.labelweight": "bold", "axes.titleweight": "bold",
    "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False,
})

fig = plt.figure(figsize=(11.8, 2.35))
gs = fig.add_gridspec(1, 4, width_ratios=[1.4, 1, 1, 1])

# ---- left: pooled UL-RB ECDF, one line per load tier (unchanged) ----
ax_ecdf = fig.add_subplot(gs[0, 0])
SERIES = [
    ("low", "Low load", "#1b9e77"),
    ("mid", "Medium load", "#d95f02"),
    ("high", "High load", "#7570b3"),
]
data = json.load(open(ECDF_DATA))
xmax = 0
for key, label, color in SERIES:
    steps = data[key]["steps"]
    x = [0] + [p[0] for p in steps]
    y = [0] + [p[1] for p in steps]
    xmax = max(xmax, x[-1])
    ax_ecdf.plot(x, y, drawstyle="steps-post", color=color, lw=1.6, label=label)
ax_ecdf.set_xlim(0, xmax * 1.05)
ax_ecdf.set_ylim(0, 1.02)
ax_ecdf.set_xlabel("UL RBs / 150ms", fontweight="bold")
ax_ecdf.set_ylabel("ECDF", fontweight="bold")
plt.setp(ax_ecdf.get_xticklabels(), fontweight="bold")
plt.setp(ax_ecdf.get_yticklabels(), fontweight="bold")
leg = ax_ecdf.legend(loc="lower right", fontsize=10, framealpha=0.9)
for txt in leg.get_texts():
    txt.set_fontweight("bold")
ax_ecdf.text(0.5, -0.5, "(a)", fontsize=13, fontweight="bold",
             ha="center", va="top", transform=ax_ecdf.transAxes)

# ---- right: closed-loop xApp A-B-A sweep, 3dB HARQ gain, panels b/c/d ----
phases = [
    {"label": "target 0.050", "mcs": 23.90, "mcs_sd": 0.30,
     "cwnd": 2557.8, "cwnd_sd": 806.9, "rate": 16.61, "rate_sd": 1.69},
    {"label": "target 0.200", "mcs": 25.00, "mcs_sd": 0.03,
     "cwnd": 526.7, "cwnd_sd": 621.2, "rate": 11.51, "rate_sd": 4.57},
    {"label": "target 0.050", "mcs": 24.00, "mcs_sd": 0.00,
     "cwnd": 2668.9, "cwnd_sd": 807.4, "rate": 16.92, "rate_sd": 1.39},
]
labels = ["0.05\n(A)", "0.20\n(B)", "0.05\n(A)"]
panels = [("mcs", "mcs_sd", "Settled\nMCS"),
          ("cwnd", "cwnd_sd", "Mean\ncwnd"),
          ("rate", "rate_sd", "Goodput\n(Mbit/s)")]
bar_colors = ["#4C72B0", "#C44E52", "#4C72B0"]
panel_tags = ["(b)", "(c)", "(d)"]

for col, (key, sdkey, ylabel) in enumerate(panels):
    ax = fig.add_subplot(gs[0, col + 1])
    vals = [p[key] for p in phases]
    errs = [p[sdkey] for p in phases]
    ax.bar(range(3), vals, yerr=errs, capsize=3, color=bar_colors,
           edgecolor="black", linewidth=0.6, width=0.62)
    ax.set_xticks(range(3))
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.set_ylabel(ylabel, fontsize=12, fontweight="bold", labelpad=2)
    ax.set_xlabel("OLLA target\nBLER", fontsize=12, fontweight="bold")
    ax.tick_params(axis="y", labelsize=11)
    plt.setp(ax.get_yticklabels(), fontweight="bold")
    ax.grid(axis="y", alpha=0.3, linewidth=0.5)
    ax.set_axisbelow(True)
    ax.text(0.5, -0.7, panel_tags[col], fontsize=13, fontweight="bold",
            ha="center", va="top", transform=ax.transAxes)

fig.subplots_adjust(left=0.055, right=0.995, top=0.97, bottom=0.5, wspace=0.55)
fig.savefig(OUT, bbox_inches="tight")
print("wrote", OUT)
