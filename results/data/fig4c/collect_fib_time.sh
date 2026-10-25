#!/bin/bash

# Initialize the CSV file with a header
echo "fib_n,trial,elapsed_ns" > fib_times.csv

# Loop over fib_n from 18 to 28 (x-axis)
for n in $(seq 18 28); do
  # For each fib_n, run 10 trials (y-axis)
  for t in $(seq 1 10); do
    # Run your program and capture the output
    output=$(./run components 1 $n 1 0)
    # Extract the elapsed time in nanoseconds from the output
    elapsed=$(echo "$output" | grep "Elapsed time" | awk '{print $4}')
    # Append the result to the CSV file
    echo "$n,$t,$elapsed" >> fib_times.csv
    # Optional: print progress to the terminal
    echo "fib($n) trial $t: $elapsed ns"
  done
done
