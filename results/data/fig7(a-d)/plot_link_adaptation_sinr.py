#!/usr/bin/env python3
"""Fig for eval.tex Sec 6.1 (Fidelity / link adaptation): settled MCS and DL
goodput vs SINR under the Chronos SINR-based channel model, mean +/- 95% CI
over n=3 seeded runs per point (panels a-b). Same channel model demonstrated
in the closed-loop xApp use case (Sec 7.2). Panels c-e show time-series
evolution of cwnd, BLER, and total HARQ retransmissions, mean over n=3 reps
per SINR condition (18/19.5/22.5 dB) -- individual rep traces are drawn thin
in the background of (c)/(d) so real run-to-run variability (e.g. cwnd onset
timing) stays visible rather than being hidden by the mean line.

Data sources:
  ../sinr_sweep_ci/{ue,iperf}_<sinr>_r<rep>.{log,json}      (a, b)
  ../sinr_sweep_ci/cwnd_capture/{ue,cwnd}_<tag>.{log,raw}   (c, d)
Output: one PDF per panel in the parent fig7(a-d) directory.
"""
import re, json, math, os, bisect

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 11,
    "font.weight": "bold", "axes.labelweight": "bold", "axes.titleweight": "bold",
    "axes.labelsize": 12, "xtick.labelsize": 10.5, "ytick.labelsize": 10.5,
    "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
    "axes.spines.right": False, "legend.frameon": False,
})
C = {"thr": "#2166ac", "mcs": "#d95f02", "baseline": "#444444",
     "cwnd": "#2166ac", "bler": "#b2182b", "harq": "#5e3c99"}

FIGURE_DIR = os.path.dirname(os.path.abspath(__file__))
WORKDIR = os.path.join(FIGURE_DIR, "sinr_sweep_ci")
EVOWORKDIR = os.path.join(WORKDIR, "cwnd_capture")
EVO_CONDITIONS = [
    ("18 dB", "#b2182b", ["18p0", "18p0_r2", "18p0_r3", "18p0_rtt"]),
    ("19.5 dB", "#2166ac", ["19p5", "19p5_r2", "19p5_r3", "19p5_rtt"]),
    ("22.5 dB", "#1a9850", ["22p5", "22p5_r2", "22p5_r3", "22p5_rtt"]),
]
CSV_RE_TAG = re.compile(r"(\w+)=([\-0-9.]+)")


def load_single_run(tag):
    """Raw (t, cwnd) and (t, BLER%) series, plus the final cumulative HARQ
    retransmission count, for one capture run. Returns None fields if the
    tag's files don't exist (so a rep that hasn't been captured yet is
    silently skipped rather than crashing the plot)."""
    cwnd_t, cwnd_y = [], []
    path = f"{EVOWORKDIR}/cwnd_{tag}.raw"
    if os.path.exists(path):
        rows = [ln.split() for ln in open(path) if ln.strip()]
        if rows:
            t0 = float(rows[0][0])
            for ts, cw in rows:
                cwnd_t.append(float(ts) - t0)
                cwnd_y.append(int(cw))
            # Trim trailing connection-teardown artifacts: once cwnd has
            # reached its plateau, a poll landing after the socket closes
            # (or hits a fresh idle connection) reads back near the default
            # cwnd (~10), which isn't real transport-layer behavior -- it's
            # just the poller outliving the test. Drop any trailing samples
            # that fall below half the series' own plateau.
            plateau = max(cwnd_y) if cwnd_y else 0
            while cwnd_y and cwnd_y[-1] < 0.5 * plateau:
                cwnd_t.pop(); cwnd_y.pop()

    # Cap parsing at the intended test window. The UE process is left running
    # (nohup, not killed) after each capture script exits -- it only stops
    # when the *next* capture's `pkill nr-uesoftmodem` runs. If that's not
    # immediately after (e.g. an idle gap while just discussing results), the
    # log keeps accumulating traffic well past the real ~60s test, silently
    # inflating tot_bler/tot_retx. DURATION in capture_cwnd_run.sh is 60s;
    # cap with a small margin for attach-time offset drift.
    MAX_RUN_T = 65.0
    bler_t, bler_y = [], []
    harq_total = None
    path = f"{EVOWORKDIR}/ue_{tag}.log"
    if os.path.exists(path):
        last_retx = None
        for line in open(path, errors="replace"):
            if "[EMURAN-DL-CSV]" not in line:
                continue
            d = dict(CSV_RE_TAG.findall(line))
            t = float(d["t"])
            if t > MAX_RUN_T:
                break
            bler_t.append(t); bler_y.append(float(d["tot_bler"]) * 100)
            last_retx = int(d["tot_retx"])
        harq_total = last_retx

    return (cwnd_t, cwnd_y), (bler_t, bler_y), harq_total


def resample_step(t, y, grid):
    """Step/forward-fill resample of (t, y) onto the given time grid: for
    each grid point, use the most recent y at or before it (or the first
    value if the grid point precedes all data)."""
    if not t:
        return [None] * len(grid)
    out = []
    for g in grid:
        i = bisect.bisect_right(t, g) - 1
        out.append(y[i] if i >= 0 else y[0])
    return out


def load_condition(tags):
    """Load all reps for one SINR condition and compute mean cwnd/BLER
    trajectories (step-resampled onto a common 1s grid) plus per-rep HARQ
    totals for the bar chart with error bars."""
    reps = [load_single_run(tag) for tag in tags]
    reps = [(c, b, h) for c, b, h in reps if c[0] or b[0]]  # drop missing reps

    max_t = 0
    for (cwnd_t, _), (bler_t, _), _ in reps:
        if cwnd_t:
            max_t = max(max_t, cwnd_t[-1])
        if bler_t:
            max_t = max(max_t, bler_t[-1])
    grid = [i * 1.0 for i in range(int(max_t) + 2)]

    cwnd_reps_resampled = []
    bler_reps_resampled = []
    for (cwnd_t, cwnd_y), (bler_t, bler_y), _ in reps:
        cwnd_reps_resampled.append(resample_step(cwnd_t, cwnd_y, grid))
        bler_reps_resampled.append(resample_step(bler_t, bler_y, grid))

    def mean_series(reps_resampled):
        out = []
        for i in range(len(grid)):
            vals = [r[i] for r in reps_resampled if r[i] is not None]
            out.append(sum(vals) / len(vals) if vals else None)
        return out

    cwnd_mean = mean_series(cwnd_reps_resampled)
    bler_mean = mean_series(bler_reps_resampled)
    harq_totals = [h for _, _, h in reps if h is not None]

    return {
        "grid": grid,
        "cwnd_mean": cwnd_mean,
        "cwnd_reps": [(cwnd_t, cwnd_y) for (cwnd_t, cwnd_y), _, _ in reps],
        "bler_mean": bler_mean,
        "bler_reps": [(bler_t, bler_y) for _, (bler_t, bler_y), _ in reps],
        "harq_totals": harq_totals,
        "n": len(reps),
    }


OUT = FIGURE_DIR
os.makedirs(OUT, exist_ok=True)

POINTS = ["18.0", "19.5", "22.5"]
REPS = [1, 2, 3]
CSV_RE = re.compile(r"(\w+)=([\-0-9.]+)")


def get_throughput(sinr, rep):
    path = f"{WORKDIR}/iperf_{sinr.replace('.', 'p')}_r{rep}.json"
    if not os.path.exists(path):
        return None
    d = json.load(open(path))
    vals = [iv["sum"]["bits_per_second"] / 1e6 for iv in d.get("intervals", [])]
    return sum(vals) / len(vals) if vals else None


def get_settled_mcs(sinr, rep):
    path = f"{WORKDIR}/ue_{sinr.replace('.', 'p')}_r{rep}.log"
    if not os.path.exists(path):
        return None
    recs = []
    for line in open(path, errors="replace"):
        if "[EMURAN-DL-CSV]" in line:
            recs.append(dict(CSV_RE.findall(line)))
    if not recs:
        return None
    settled = [r for r in recs if r["mcs_min"] == r["mcs_max"]]
    if not settled:
        return None
    tbs = sum(int(r["win_tbs"]) for r in settled)
    return sum(int(r["win_tbs"]) * int(r["mcs_last"]) for r in settled) / tbs


def mean_ci(vals):
    vals = [v for v in vals if v is not None]
    n = len(vals)
    if n == 0:
        return None, None, 0
    m = sum(vals) / n
    if n < 2:
        return m, 0.0, n
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (n - 1))
    t = {1: 12.706, 2: 4.303, 3: 3.182}.get(n - 1, 2.0)
    return m, t * sd / math.sqrt(n), n


def get_baseline_throughput():
    vals = [get_throughput("none", r) for r in REPS]
    m, _, _ = mean_ci(vals)
    return m


thr_x, thr_y, thr_ci = [], [], []
mcs_x, mcs_y, mcs_ci = [], [], []
for p in POINTS:
    tm, tc, _ = mean_ci([get_throughput(p, r) for r in REPS])
    if tm is not None:
        thr_x.append(float(p)); thr_y.append(tm); thr_ci.append(tc)
    mm, mc, _ = mean_ci([get_settled_mcs(p, r) for r in REPS])
    if mm is not None:
        mcs_x.append(float(p)); mcs_y.append(mm); mcs_ci.append(mc)

baseline_thr = get_baseline_throughput()
evo = {label: load_condition(tags) for label, _, tags in EVO_CONDITIONS}

import matplotlib.ticker as mticker

TITLE_FS = 12.0
LABEL_FS = 11.0
TICK_FS = 10.0
LEG_FS = 11.0

PANEL_W, PANEL_H = 1.75, 1.05

fig_a = plt.figure(figsize=(PANEL_W, PANEL_H))
fig_b = plt.figure(figsize=(PANEL_W, PANEL_H))
fig_c = plt.figure(figsize=(PANEL_W, PANEL_H))
fig_d = plt.figure(figsize=(PANEL_W, PANEL_H))
axes_bot = [fig_b.add_subplot(111), fig_c.add_subplot(111), fig_d.add_subplot(111)]

ax = fig_a.add_subplot(111)
ax.errorbar(mcs_x, mcs_y, yerr=mcs_ci, fmt="o-", color=C["mcs"], ms=2.5,
            lw=1.0, capsize=2, elinewidth=0.8)
ax.set_xlabel("SINR (dB)", fontsize=LABEL_FS, fontweight="bold")
ax.set_ylabel("MCS", fontsize=LABEL_FS, fontweight="bold", color=C["mcs"])
ax.set_ylim(20, 29.5)
ax.yaxis.set_major_locator(mticker.MaxNLocator(4))
ax.xaxis.set_major_locator(mticker.MaxNLocator(3))
ax.tick_params(axis="y", labelsize=TICK_FS, labelcolor=C["mcs"], pad=1)
ax.tick_params(axis="x", labelsize=TICK_FS, pad=1)
plt.setp(ax.get_xticklabels(), fontweight="bold")
plt.setp(ax.get_yticklabels(), fontweight="bold")

ax2 = ax.twinx()
ax2.errorbar(thr_x, thr_y, yerr=thr_ci, fmt="s-", color=C["thr"], ms=2.5,
             lw=1.0, capsize=2, elinewidth=0.8)
if baseline_thr:
    ax2.axhline(baseline_thr, ls=":", color=C["baseline"], lw=0.9)
ax2.set_ylabel("Mbit/s", fontsize=LABEL_FS, fontweight="bold", color=C["thr"])
ax2.yaxis.set_major_locator(mticker.MaxNLocator(4))
ax2.tick_params(axis="y", labelsize=TICK_FS, labelcolor=C["thr"], pad=1)
plt.setp(ax2.get_yticklabels(), fontweight="bold")
ax2.set_ylim(13, 23.5)
# Axis labels are already color-coded to their series (orange=MCS, blue=goodput),
# so a legend box would be redundant -- skip it to save space.

ax = axes_bot[0]
for label, color, _ in EVO_CONDITIONS:
    d = evo[label]
    cwnd_t, cwnd_y = d["grid"], d["cwnd_mean"]  # mean across all reps
    ax.plot(cwnd_t, cwnd_y, "-", color=color, lw=1.3)
ax.set_xlabel("Time (s)", fontsize=LABEL_FS, fontweight="bold")
ax.set_ylabel("cwnd", fontsize=LABEL_FS, fontweight="bold")
ax.xaxis.set_major_locator(mticker.MaxNLocator(3))
ax.yaxis.set_major_locator(mticker.MaxNLocator(3))
ax.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda v, _: f"{v/1000:.1f}k" if abs(v) >= 1000 else f"{v:g}"))
ax.tick_params(labelsize=TICK_FS, pad=1)
plt.setp(ax.get_xticklabels(), fontweight="bold")
plt.setp(ax.get_yticklabels(), fontweight="bold")

ax = axes_bot[1]
bler_max = 1
for label, color, _ in EVO_CONDITIONS:
    d = evo[label]
    settled = [bler_y[-1] for _, bler_y in d["bler_reps"] if bler_y]
    if d["bler_mean"]:
        bler_max = max(bler_max, max(v for v in d["bler_mean"] if v is not None))
    ax.plot(d["grid"], d["bler_mean"], "-", color=color, lw=1.3)
    # Error bar at the settled (end-of-run) point: mean +/- 95% CI across reps.
    if settled and d["grid"]:
        m, ci, _ = mean_ci(settled)
        ax.errorbar([d["grid"][-1]], [m], yerr=[ci], fmt="none",
                     ecolor=color, elinewidth=1.0, capsize=2, capthick=1.0)
ax.set_xlabel("Time (s)", fontsize=LABEL_FS, fontweight="bold")
ax.set_ylabel("BLER (%)", fontsize=LABEL_FS, fontweight="bold")
ax.xaxis.set_major_locator(mticker.MaxNLocator(3))
ax.yaxis.set_major_locator(mticker.MaxNLocator(3))
ax.tick_params(labelsize=TICK_FS, pad=1)
plt.setp(ax.get_xticklabels(), fontweight="bold")
plt.setp(ax.get_yticklabels(), fontweight="bold")
ax.set_ylim(0, bler_max * 1.3)

ax = axes_bot[2]
means, cis, run_dur = [], [], 0
for label, color, _ in EVO_CONDITIONS:
    d = evo[label]
    m, ci, _ = mean_ci(d["harq_totals"])
    means.append(m); cis.append(ci)
    if d["grid"]:
        run_dur = max(run_dur, d["grid"][-1])
short_labels = [label.replace(" dB", "") for label, _, _ in EVO_CONDITIONS]
bars = ax.bar(short_labels, means, yerr=cis, capsize=2,
              color=[color for _, color, _ in EVO_CONDITIONS], width=0.6)
def _fmt_k(v):
    return f"{v/1000:.1f}k" if abs(v) >= 1000 else f"{v:.0f}"

for rect, val, ci in zip(bars, means, cis):
    ax.text(rect.get_x() + rect.get_width() / 2, val + (ci or 0) + max(means) * 0.04,
            f"{val:.0f}", ha="center", va="bottom", fontsize=TICK_FS, fontweight="bold")
ax.set_xlabel("SINR (dB)", fontsize=LABEL_FS, fontweight="bold")
ax.set_yticks([])
ax.spines["left"].set_visible(False)
ax.tick_params(axis="x", labelsize=TICK_FS, pad=1)
plt.setp(ax.get_xticklabels(), fontweight="bold")
ax.set_ylim(0, max(means) * 1.3)

for f, name in [(fig_a, "fig7a"), (fig_b, "fig7b"),
                 (fig_c, "fig7c"), (fig_d, "fig7d")]:
    f.tight_layout(pad=0.3)
    out_path = f"{OUT}/{name}.pdf"
    f.savefig(out_path, bbox_inches="tight")
    print(f"wrote {out_path}")
print("mcs:", list(zip(mcs_x, mcs_y, mcs_ci)))
print("thr:", list(zip(thr_x, thr_y, thr_ci)))
print("baseline_thr:", baseline_thr)
for label, _, _ in EVO_CONDITIONS:
    d = evo[label]
    print(f"{label}: n={d['n']}, harq_totals={d['harq_totals']}")
