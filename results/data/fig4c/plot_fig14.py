import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Read both csv files
chronos = pd.read_csv("chronos.csv")
linux = pd.read_csv("non-chronos.csv")

# Drop the "trial" column if present
if 'trial' in chronos.columns:
    chronos = chronos.drop(columns=['trial'])
if 'trial' in linux.columns:
    linux = linux.drop(columns=['trial'])

# Select the x-axis values to plot, in display order
fib_ns = [22, 24, 26, 28]
columns_to_plot = [str(fib_n) for fib_n in fib_ns]

# Compute mean processing time for each fib_n
chronos_means = chronos[columns_to_plot].mean(axis=0)
linux_means = linux[columns_to_plot].mean(axis=0)

# Bar width and x locations
bar_width = 0.35
x = np.arange(len(fib_ns))

fig = plt.figure(figsize=(2,2.5))

# Chronos (left bar, blue)
plt.bar(x - bar_width/2, chronos_means, width=bar_width, label='Chronos', color='#1f77b4', edgecolor='black', linewidth=1.5)
# Linux (right bar, orange)
plt.bar(x + bar_width/2, linux_means, width=bar_width, label='Linux', color='#ff7f0e', edgecolor='black', linewidth=1.5)

# Add y=1e6 horizontal dashed line (not in legend)
plt.axhline(y=1e6, color='gray', linestyle='--', linewidth=2, zorder=0)

plt.xlabel('Task Size (n)', fontsize=14)
plt.ylabel('Task Time (ms)', fontsize=14)
plt.xticks(x, fib_ns, fontsize=12)
plt.yticks([1e6,2e6,3e6,4e6,5e6], [1,2,3,4,5], fontsize=12)
plt.legend(fontsize=9)
plt.tight_layout()
fig.text(0.01, 0.01, '(c)', ha='left', va='bottom',
         fontsize=10, fontweight='bold')
plt.savefig('fig4c.pdf', dpi=300)
