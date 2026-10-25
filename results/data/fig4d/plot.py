import csv
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

# Resolved against this file rather than the working directory, so the master
# script can invoke it from the repository root.
HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_CSV = os.path.join(HERE, "client.csv")
SERVER_CSV = os.path.join(HERE, "server.csv")
OUTPUT_PDF = os.path.join(HERE, "fig4d.pdf")

# =========================
# Check files exist
# =========================
for f in [CLIENT_CSV, SERVER_CSV]:
    if not os.path.exists(f):
        print(f"ERROR: CSV file {f} does not exist.")
        exit(1)

# =========================
# Load CSV
# =========================
def load_csv(filename):
    data = {}
    with open(filename, newline="") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) != 3:
                continue
            try:
                N = int(row[0])
                diff = float(row[2])
                data[N] = diff
            except:
                continue
    return data

client_data = load_csv(CLIENT_CSV)
server_data = load_csv(SERVER_CSV)

# =========================
# Find requested Ns present in both datasets
# =========================
requested_Ns = [100, 1000, 10000]
tick_labels = {100: "100", 1000: "1k", 10000: "10k"}
common_Ns = [N for N in requested_Ns if N in client_data and N in server_data]
missing_Ns = [N for N in requested_Ns if N not in client_data or N not in server_data]

if missing_Ns:
    print("WARNING: Requested N values missing from client.csv or server.csv:", missing_Ns)

client_values = [client_data[N] for N in common_Ns]
server_values = [server_data[N] for N in common_Ns]

# =========================
# Plotting
# =========================
x = np.arange(len(common_Ns))
bar_width = 0.35

fig = plt.figure(figsize=(1.8,2.5))

bars1 = plt.bar(x + bar_width/2, server_values, bar_width,
                label="Chronos", color='tab:blue',
                edgecolor='black', linewidth=1.5)
bars2 = plt.bar(x - bar_width/2, client_values, bar_width,
                label="Linux", color='tab:orange',
                edgecolor='black', linewidth=1.5)

plt.xlabel("Task Iterations", fontsize=14, x=0.2)
plt.ylabel("Sync. Loss (ms)", fontsize=14)
plt.xticks(x, [tick_labels[N] for N in common_Ns], fontsize=10)
plt.yticks(fontsize=12)
plt.yscale("log")
plt.legend(fontsize=9, loc="lower center", bbox_to_anchor=(0.5, 1.02))

plt.tight_layout()
fig.text(0.01, 0.01, '(d)', ha='left', va='bottom',
         fontsize=10, fontweight='bold')

# =========================
# Save figure as PDF
# =========================
plt.savefig(OUTPUT_PDF, dpi=300)
print(f"Figure saved as {OUTPUT_PDF}")

# =========================
# Display the plot
# =========================
