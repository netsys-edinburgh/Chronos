import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter

FIGURE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(FIGURE_DIR, "parsed_data", "fig8b_data.csv")
_data = np.genfromtxt(CSV_PATH, delimiter=",", skip_header=1)
scale = _data[:, 0]
avg_ue_tput = _data[:, 1]
tput_err = _data[:, 2]
dilation_factor = _data[:, 3]


plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.weight": "bold",
    "axes.labelweight": "bold",
    "axes.labelsize": 16,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
})

fig, ax1 = plt.subplots(figsize=(6, 2))

fig.subplots_adjust(
    left=82.08 / 432,
    right=359.656 / 432,
    bottom=(144 - 94.12) / 144,
    top=(144 - 10.8) / 144,
)


ax1.set_xscale("log")
ax1.errorbar(
    scale,
    avg_ue_tput,
    yerr=tput_err,
    fmt="o-",
    color="tab:blue",
    linewidth=2,
    markersize=7,
    capsize=4,
    elinewidth=2,
)
ax1.set_xlabel("Scale (Number of UE / gNB)")
ax1.set_ylabel("Avg UE Tput\n(Mbps)", color="tab:blue")
ax1.tick_params(axis="y", labelcolor="tab:blue")
ax1.set_ylim(0, avg_ue_tput.max() * 1.5)
ax1.set_yticks([0, 10])

ax1.set_xticks([1, 10, 100])
ax1.xaxis.set_major_formatter(ScalarFormatter())

ax2 = ax1.twinx()
ax2.set_yscale("log")
ax2.plot(
    scale,
    dilation_factor,
    "s--",
    color="tab:red",
    linewidth=2,
    markersize=7,
)
ax2.set_ylabel("Dilation\nFactor", color="tab:red")
ax2.tick_params(axis="y", labelcolor="tab:red")
ax2.set_yticks([1, 10])
ax2.yaxis.set_major_formatter(ScalarFormatter())


for ax in (ax1, ax2):
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_fontweight("bold")


fig.savefig(os.path.join(FIGURE_DIR, "fig8b.pdf"))
plt.close(fig)
