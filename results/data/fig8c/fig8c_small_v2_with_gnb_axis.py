import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, FixedLocator, FixedFormatter, NullLocator

FIGURE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(FIGURE_DIR, "gNB_DILATION", "results.csv")
rows = list(csv.DictReader(open(CSV_PATH)))
recs = [r for r in rows if r["run"] in ("5g_nr_rerun", "5g_nr") and int(r["n_ue_attached"]) <= 510
        and int(r["n_ue_target"]) == int(r["n_gnb"]) * 15]
recs = sorted(recs, key=lambda r: int(r["n_ue_attached"]))
ue = [int(r["n_ue_attached"]) for r in recs]
dilation = [float(r["mean_dilation"]) for r in recs]
dilation_err = [float(r["sd_dilation"]) for r in recs]

LABEL_FS, TICK_FS = 6.5, 5.5
X_LABEL_FS, X_TICK_FS = 5.0, 4.5
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.weight": "bold",
    "axes.labelweight": "bold",
})

fig, ax = plt.subplots(figsize=(1.20, 0.95), dpi=300)
fig.subplots_adjust(left=0.24, right=0.97, bottom=0.24, top=0.78)

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(15, 500)
ax.set_ylim(bottom=1)
ax.errorbar(ue, dilation, yerr=dilation_err, fmt="s--", color="tab:red",
            linewidth=0.8, markersize=1.8, capsize=1.5, elinewidth=0.6)
ax.set_xlabel("UEs Attached", fontsize=X_LABEL_FS, fontweight="bold", labelpad=1)
ax.set_ylabel("Dilation Factor", fontsize=LABEL_FS, fontweight="bold", labelpad=1)
ax.set_xticks([15, 100, 500])
ax.xaxis.set_major_formatter(ScalarFormatter())
ax.xaxis.set_minor_locator(NullLocator())
ax.set_yticks([1, 10])
ax.yaxis.set_major_formatter(ScalarFormatter())
ax.tick_params(axis="y", labelsize=TICK_FS, pad=1, length=2, width=0.6)
ax.tick_params(axis="x", labelsize=X_TICK_FS, pad=1, length=2, width=0.6)
for spine in ax.spines.values():
    spine.set_linewidth(0.6)

for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight("bold")

# Secondary x-axis (top): number of gNBs, fixed 15 UE/gNB ratio.
ax2 = ax.twiny()
ax2.set_xscale("log")
ax2.set_xlim(ax.get_xlim())
gnb_ticks_ue = [15, 100, 500]
gnb_ticks_labels = [f"{v/15:.0f}" if v/15 >= 1 else f"{v/15:.1f}" for v in gnb_ticks_ue]
ax2.xaxis.set_major_locator(FixedLocator(gnb_ticks_ue))
ax2.xaxis.set_major_formatter(FixedFormatter(gnb_ticks_labels))
ax2.xaxis.set_minor_locator(NullLocator())
ax2.set_xlabel("Number of gNBs", fontsize=X_LABEL_FS, fontweight="bold", labelpad=1)
ax2.tick_params(axis="x", labelsize=X_TICK_FS, pad=1, length=2, width=0.6)
for spine in ax2.spines.values():
    spine.set_linewidth(0.6)
for label in ax2.get_xticklabels():
    label.set_fontweight("bold")

fig.savefig(os.path.join(FIGURE_DIR, "fig8c.pdf"))
print("wrote fig8c.pdf")
print(list(zip(ue, dilation, dilation_err)))
