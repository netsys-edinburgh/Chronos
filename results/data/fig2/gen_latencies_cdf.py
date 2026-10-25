import seaborn
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
import glob
import numpy as np

seaborn.color_palette("tab10")
seaborn.set_context("talk", font_scale=0.9)

# Filename to machine type mapping
osnoise_machine_types = {
    "aws-c7i-flex.2xlarge.log": "AWS Compute-Optimised (Cheap)",
    "aws-c7i.2xlarge.log": "AWS Compute-Optimised",
    "aws-m7i-flex.2xlarge.log": "AWS General (Cheap)",
    "aws-m7i.2xlarge.log": "AWS General",
    "gcp-c2d-highcpu-8.log": "GCP Compute-Optimised",
    "gcp-e2-standard-8.log": "GCP General",
    "azure-standard-b8ms.log": "Azure General (Cheap)",
    "azure-standard-d8s-v3.log": "Azure General",
    "powder-d430.log": "CloudLab (Old)",
    "powder-c6620.log": "CloudLab"
}


# Filename to machine type mapping
ping_machine_types = {
    "aws-c7i-flex.ping.log": "AWS Compute-Optimised (Cheap)",
    "aws-c7i.ping.log": "AWS Compute-Optimised",
    "aws-m7i-flex.ping.log": "AWS General (Cheap)",
    "aws-m7i.ping.log": "AWS General",
    "gcp-c2d-highcpu-8.ping.log": "GCP Compute-Optimised",
    "gcp-e2-standard-8.ping.log": "GCP General",
    "azure-standard-b8ms.ping.log": "Azure General (Cheap)",
    "azure-standard-d8s-v3.ping.log": "Azure General",
    "powder-d710.ping.log": "CloudLab (Old)",
    "powder-c6620.ping.log": "CloudLab"
}


# Create a np array of three variables, machine type, latency and probability
def parse_osnoise_logs():
    data = pd.DataFrame()
    # data = np.empty(shape=(0, 3), dtype=object)

    # Get all the log files in the directory and loop through them
    files = glob.glob("osnoise/*.log")
    i = 0
    for filename in files:
        filename_only = filename.split("/")[-1]
        print(f"Processing file: {filename_only}")

        if filename_only not in osnoise_machine_types:
            print(f"Warning: {filename_only} not found in osnoise_machine_types, skipping...")
            continue

        machine_type = osnoise_machine_types[filename_only]

        start_parsing = False
        raw_counts = []
        total_datapoints = 0
        with open(filename, "r") as f:
            i += 1
            print(f"Parsing file ({i}/{len(files)}): {filename}")
            for line in f:
                if (
                    line
                    == "Index   CPU-001   CPU-002   CPU-003   CPU-004   CPU-005   CPU-006   CPU-007\n"
                ):
                    start_parsing = True
                    continue
                elif line.startswith("over:"):
                    # For the "Over" category, just be generous and assume that it was
                    # at most 10us over - we have no way of telling
                    bucket = max([b for b,a,m in raw_counts if m == machine_type]) + 10
                    amount = sum(map(int, line.split()[1:]))
                    if amount == 0: continue
                elif line.startswith("count:"):
                    start_parsing = False
                    total_datapoints = sum(map(int, line.split()[1:]))
                    break
                elif start_parsing:
                    bucket = int(line.split()[0])
                    amount = sum(map(int, line.split()[1:]))
                else:
                    continue

                # Handle powder-d430 which has 10us intervals - interpolate to 1us intervals
                if filename_only == "powder-d430.log" and bucket > 0:
                    # Distribute the count across the 10 microseconds represented by this bucket
                    # Each bucket represents latencies from bucket to bucket+9 microseconds
                    for sub_bucket in range(bucket, bucket + 10):
                        raw_counts.append([sub_bucket, amount // 10, machine_type])
                else:
                    raw_counts.append([bucket, amount, machine_type])

        df = pd.DataFrame(
            raw_counts, columns=["Interrupt Latency (us)", "Count", "Machine Type"]
        )

        df["CDF"] = (
            pd.Series(np.cumsum(np.pad(df["Count"].to_numpy(), (1, 0), "constant")))
            / total_datapoints
        )
        data = pd.concat([data, df], ignore_index=True)
    return data


# Create a np array of three variables, machine type, latency and probability
def ping_parse_logs():
    data = pd.DataFrame()

    # Get all the log files in the directory and loop through them
    files = glob.glob("ping/*.log")
    i = 0
    for filename in files:
        filename_only = filename.split("/")[-1]
        print(f"Processing ping file: {filename_only}")

        if filename_only not in ping_machine_types:
            print(f"Warning: {filename_only} not found in ping_machine_types, skipping...")
            continue

        machine_type = ping_machine_types[filename_only]

        start_parsing = False
        raw_ms = []
        with open(filename, "r") as f:
            i += 1
            print(f"Parsing file ({i}/{len(files)}): {filename}")
            for line in f:
                if line.startswith("PING "):
                    start_parsing = True
                    continue
                elif line.strip() == "" or line.startswith("--- "):
                    start_parsing = False
                    break

                if start_parsing:
                    ms = float(line.split("time=")[1].split(" ")[0])

                    raw_ms.append(int(ms * 1000))

        df = pd.DataFrame(raw_ms, columns=["Network Latency (µs)"])
        df = df.sort_values(by=["Network Latency (µs)"], ignore_index=True)

        count, bins_count = np.histogram(
            df["Network Latency (µs)"].to_numpy(), bins=100
        )
        pdf = count / count.sum()

        prob_df = pd.DataFrame()
        prob_df["Network Latency (µs)"] = bins_count[1:]
        # # Now create a dataframe with just cmulative probability and machine type
        prob_df["Machine Type"] = machine_type
        prob_df["CDF"] = pd.Series(np.cumsum(np.pad(pdf, (1, 0), "constant")))

        data = pd.concat([data, prob_df], ignore_index=True)

    return data


def graph_data(noise_df: pd.DataFrame, ping_df: pd.DataFrame):
    noise_df = noise_df.sort_values(by=["Interrupt Latency (us)"])
    ping_df = ping_df.sort_values(by=["Network Latency (µs)"])

    fig, axes = plt.subplots(ncols=2, figsize=(16, 4.2))

    # sns.boxplot(x="species", y=col, data=iris, hue="species", dodge=False, ax=ax)
    # ax.get_legend().remove()
    # ax.set_title(col)

    noise_df["CDF"] = 1 - noise_df["CDF"]

    # Create a CDF plot
    myplot = seaborn.lineplot(
        ax=axes[0],
        x="Interrupt Latency (us)",
        y="CDF",
        hue="Machine Type",
        data=noise_df,
        hue_order=sorted(ping_machine_types.values()),
    )
    # myplot.set_xscale("symlog", base=10, linthresh=0.1)
    myplot.set_xlim(-10, 600)
    myplot.set_yscale("symlog", base=10, linthresh=0.00001)
    myplot.set_ylim(1.00, 0.00001)

    myplot.vlines([500], 0, 1, colors=["black"], linestyles="dotted", linewidth=2)
    myplot.text(
        490,
        0.2,
        "100% of slot time",
        color="black",
        fontweight="bold",
        fontsize=11,
        transform=myplot.get_xaxis_transform(),
        va="top",
        ha="right",
    )

    locmin = mticker.LogLocator(base=10, subs=np.arange(0.1, 1, 0.1), numticks=10)
    myplot.yaxis.set_minor_locator(locmin)
    myplot.yaxis.set_minor_formatter(mticker.NullFormatter())

    # Restore the minor ticks for log scale on x-axis
    # locmin = mticker.LogLocator(base=10, subs=np.arange(0.1, 1, 0.1), numticks=10)
    # myplot.xaxis.set_minor_locator(locmin)
    # myplot.xaxis.set_minor_formatter(mticker.NullFormatter())

    # Custom Y-axis ticks
    myplot.set_yticks([1, 0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001])
    myplot.set_yticklabels(
        ["0", "0.9", "0.99", "0.999", "0.9999", "0.99999", "1.0"], weight="bold"
    )
    for label in myplot.get_xticklabels():
        label.update({"weight": "bold"})
    for label in myplot.get_yticklabels():
        label.update({"weight": "bold"})
    myplot.set_xlabel("Interrupt Latency (µs)", fontweight="bold")
    myplot.get_yaxis().label.set_visible(False)
    # myplot.set_ylabel("Cumulative Probability", fontweight="bold")
    myplot.legend().remove()

    box = myplot.get_position()
    myplot.set_position(
        [box.x0 - 0.01, box.y0 + box.height * 0.3, box.width - 0.01, box.height * 0.7]
    )

    # Create a CDF plot

    myplot = seaborn.lineplot(
        x="Network Latency (µs)",
        y="CDF",
        hue="Machine Type",
        data=ping_df,
        hue_order=sorted(ping_machine_types.values()),
    )
    # myplot.set_xscale("log")
    myplot.set_xlim(0, 1300)
    myplot.set_yscale("symlog", linthresh=0.0001)
    myplot.set_ylim(0, 1.00)

    myplot.vlines([500], 0, 1, colors=["black"], linestyles="dotted", linewidth=2)
    myplot.text(
        510,
        0.7,
        "100% of slot time",
        color="black",
        fontweight="bold",
        fontsize=11,
        transform=myplot.get_xaxis_transform(),
    )

    # Restores minor ticks
    locmin = mticker.LogLocator(base=10, subs=np.arange(0.1, 1, 0.1), numticks=10)
    myplot.yaxis.set_minor_locator(locmin)
    myplot.yaxis.set_minor_formatter(mticker.NullFormatter())

    plt.xticks(fontweight="bold")
    plt.yticks(fontweight="bold")
    myplot.set_xlabel("Network Latency (µs)", fontweight="bold")
    myplot.get_yaxis().label.set_visible(False)
    # myplot.set_ylabel("Cumulative Probability", fontweight="bold")
    myplot.legend().remove()

    box = myplot.get_position()
    myplot.set_position(
        [box.x0, box.y0 + box.height * 0.3, box.width + 0.05, box.height * 0.7]
    )

    handles, labels = myplot.get_legend_handles_labels()
    # print(handles, labels)

    # plt.xlabel("Interrupt Latency (µs)", fontweight="bold")
    # plt.ylabel("Cumulative Probability", fontweight="bold")
    fig.legend(
        handles,
        labels,
        # title="Machine Type",
        # title_fontsize="medium",
        # title_fontweight="bold",
        bbox_to_anchor=(0.5, 0),
        loc="lower center",
        bbox_transform=fig.transFigure,
        ncol=4,
        fontsize="small",
        prop={"weight": "bold", "size": 11},
        # frameon=False,
        facecolor=(1, 1, 1),
        framealpha=0.7,
    )

    plt.savefig(
        "fig2.pdf",
        format="pdf",
        dpi=1000,
        bbox_inches="tight",
    )


if __name__ == "__main__":
    osnoise_data = parse_osnoise_logs()
    ping_data = ping_parse_logs()
    # np.savetxt("foo.csv", data, delimiter=",", fmt="%s")
    graph_data(osnoise_data, ping_data)
