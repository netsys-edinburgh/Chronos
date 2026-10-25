import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load CSV
df = pd.read_csv("plot_results.csv")

# Sort by Number of UE (ascending)
df = df.sort_values(by="Number of UE")

# Extract columns (exact names as specified)
ue = df["Number of UE"]
one_proxy = df["1 Proxy"]
two_proxy = df["2 Proxy"]

# Convert to CPU percentage
one_proxy_pct = (one_proxy / 8) * 100
two_proxy_pct = (two_proxy / 8) * 100

# Bar settings
bar_width = 0.35
x = np.arange(len(ue))

plt.figure(figsize=(1.8,3))

# Bars (side-by-side)
plt.bar(
    x - bar_width/2,
    one_proxy_pct,
    bar_width,
    label="1",
    edgecolor='black',
    linewidth=1.5
)

plt.bar(
    x + bar_width/2,
    two_proxy_pct,
    bar_width,
    label="2",
    edgecolor='black',
    linewidth=1.5
)

# Axis labels
plt.xlabel("#UE", fontsize=14)
plt.ylabel("CPU Utilization (%)", fontsize=14)

# Ticks
plt.xticks(x, ue, fontsize=14)
plt.yticks(fontsize=14)

# Legend
plt.legend(fontsize=9, loc='upper left')

# Layout
plt.tight_layout()

# Save
plt.savefig("fig9d.pdf")
