import subprocess
import pandas as pd
import argparse

# Argument parser for last argument control
parser = argparse.ArgumentParser(description="Collect fib elapsed times and save as matrix CSV.")
parser.add_argument('--last-arg', type=int, default=0, choices=[0,1],
                    help='Value for the last argument in ./run (default: 0)')
args = parser.parse_args()

fib_n_list = list(range(18, 29))  # 18 to 28
trials = 10

results = []

for t in range(trials):
    row = []
    for fib_n in fib_n_list:
        # Use the argument from user
        cmd = ['./run', 'components', '1', str(fib_n), '1', str(args.last_arg)]
        try:
            completed = subprocess.run(cmd, capture_output=True, text=True, check=True)
            # Parse the Elapsed time from output
            for line in completed.stdout.splitlines():
                if 'Elapsed time' in line:
                    elapsed = line.strip().split()[-1]
                    row.append(elapsed)
                    break
            else:
                row.append('')
        except Exception as e:
            row.append('')
            print(f"Error running fib_n={fib_n} trial={t+1}: {e}")
    results.append(row)

# Write to CSV in matrix format
df = pd.DataFrame(results, columns=fib_n_list)
df.index = range(1, trials+1)
df.index.name = 'trial'
df.to_csv('fib_times_matrix.csv')
print("Saved results to fib_times_matrix.csv")
