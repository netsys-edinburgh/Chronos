# Reproducing Figure 14: Emulated Processing Time Analysis

This directory provides scripts and workflow to reproduce Figure 14 in our paper, which compares the emulated processing time for increasing Fibonacci workload sizes, running on both the Chronos Hypervisor and an unmodified Linux system.

## 1. `run` Program

The `run` executable is a C program for measuring the elapsed (emulated) processing time of computing Fibonacci numbers.

**Usage:**
```
./run <Component IP File> <fib_start_n> <fib_end_n> <fib_step> <dilated>
```
- `<Component IP File>`: The file listing component IPs (not used in non-dilated mode; may be a placeholder).
- `<fib_start_n>`: The starting Fibonacci number (e.g., 18).
- `<fib_end_n>`: The ending Fibonacci number (e.g., 28).
- `<fib_step>`: The step size between Fibonacci numbers (e.g., 1).
- `<dilated>`: `1` for Chronos Hypervisor mode, `0` for Linux mode.

The program prints the elapsed time in nanoseconds for each Fibonacci workload.

## 2. `collect_fib_time.py`

`collect_fib_time.py` automates the process of running the `run` program for a range of Fibonacci numbers and collects the results into a CSV file.

**How it works:**
- Loops over Fibonacci numbers (e.g., 18 to 28 as used in Fig 14).
- For each Fibonacci number, runs the workload (one trial per n for Fig 14).
- Collects the elapsed time output from `run`.
- Saves the results in a matrix-style CSV file, where each row is a trial and each column is a Fibonacci workload size.

**Example output CSV:**
- `chronos.csv`: Chronos Hypervisor results (`dilated=1`)
- `non-chronos.csv`: Linux results (`dilated=0`)

## 3. `plot_fig14.py`

This script reads the generated CSV files and plots the results as a grouped bar chart, similar to Figure 14.

- The x-axis represents the Fibonacci workload size (`n`).
- The y-axis is the mean emulated processing time (in nanoseconds).
- Two bars for each workload size: one for Chronos Hypervisor and one for Linux.
- The plot is saved as `fig14_emulated_time_color.png`.

## Typical Workflow

1. **Collect data for Chronos Hypervisor:**
   ```
   python collect_fib_time.py --last-arg 1
   # Produces chronos.csv
   ```
2. **Collect data for Linux:**
   ```
   python collect_fib_time.py --last-arg 0
   # Produces non-chronos.csv
   ```
3. **Plot the results:**
   ```
   python plot_fig14.py
   # Produces fig14_emulated_time_color.png
   ```

## Note

- For Figure 14, each Fibonacci workload is run only once per trial (no per-n repeat times).
- You can open the resulting CSV files in Excel or process them further for statistics.

---
