import csv
import os
import matplotlib.pyplot as plt

# 4G LTE dilation factor vs UE/eNB scale (Fig. 19 / Appendix E).
FIGURE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(FIGURE_DIR, "gNB_DILATION", "results.csv")
rows = list(csv.DictReader(open(CSV_PATH)))
rows.sort(key=lambda r: int(r["n_gnb"]))

enb = [int(r["n_gnb"]) for r in rows]
ue = [int(r["n_ue_attached"]) for r in rows]
dilation = [float(r["mean_dilation"]) for r in rows]
err = [float(r["sd_dilation"]) for r in rows]

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.weight": "bold",
    "axes.labelweight": "bold",
    "axes.labelsize": 13,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

fig, ax = plt.subplots(figsize=(5, 3.2))
labels = [f"{u} UE\n({n} eNB)" for u, n in zip(ue, enb)]
bars = ax.bar(labels, dilation, yerr=err, capsize=5, color="tab:red", width=0.55, ecolor="#333333")
for rect, val in zip(bars, dilation):
    ax.text(rect.get_x() + rect.get_width() / 2, val + 0.15, f"{val:.2f}",
            ha="center", va="bottom", fontweight="bold", fontsize=12)
ax.set_ylabel("Dilation Factor")
ax.set_ylim(0, max(dilation) * 1.35)
for label in ax.get_xticklabels() + ax.get_yticklabels():
    label.set_fontweight("bold")
fig.tight_layout()
fig.savefig(os.path.join(FIGURE_DIR, "fig19.pdf"))
print("wrote fig19.pdf")
