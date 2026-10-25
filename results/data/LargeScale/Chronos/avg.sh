#!/bin/bash

echo "Reading logs from $1, saving to $1/rtt.log"
cat $1/ue-*-dp.log | grep "rtt=" | awk -F ' ' '{ print $2 }' | awk -F '=' '{ print $2 }' > "$1/rtt.log"

NUM_RTT=$(wc -l "$1/rtt.log")
echo "Found $NUM_RTT RTTs"

python3 - << EOF
import statistics
datas = []
with open(f"$1/rtt.log") as f:
	for line in f:
		line = line.strip()
		if line == '': continue
		if line.endswith("ms"):
			line = float(line.replace("ms", ""))
		elif line[-1] == "s" and line[-2].isdigit():
			line = float(line.replace("s", "")) * 1000
		else:
			raise Exception("Unknown format {line}")
		datas.append(line)
print(f'Number of values: {len(datas)}')
print(f'Mean: {statistics.mean(datas):.2f}, median: {statistics.median(datas):.2f}, stdev: {statistics.stdev(datas):.2f}')
EOF
