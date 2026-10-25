import subprocess
import threading
import time
import csv
import re
import sys
import os

PYTHON = "python3"
SERVER_SCRIPT = "server.py"
CLIENT_SCRIPT = "client.py"

SERVER_HOST = "127.0.0.1"
CSV_FILE = "results.csv"

RUNS_PER_EXPERIMENT = 5


def stream_output(pipe, prefix):
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line}", end='')
    pipe.close()


def extract_time(output):
    match = re.search(r"Elapsed time:\s*([0-9.]+)", output)
    if match:
        return float(match.group(1))
    raise RuntimeError("Could not parse elapsed time:\n" + output)


def run_experiment(N, F, CLIENTS, mode):

    server_proc = None

    if mode == "server":

        server_proc = subprocess.Popen(
            [PYTHON, SERVER_SCRIPT, str(CLIENTS)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        threading.Thread(
            target=stream_output,
            args=(server_proc.stdout, "SERVER"),
            daemon=True
        ).start()

        time.sleep(2)

    clients = []

    for _ in range(CLIENTS):

        cmd = [PYTHON, CLIENT_SCRIPT, str(N), str(F)]

        if mode == "server":
            cmd.append(SERVER_HOST)

        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        clients.append(p)

    times = []

    for p in clients:

        stdout, stderr = p.communicate()

        if stderr:
            print(stderr)

        t = extract_time(stdout)
        times.append(t)

    if server_proc:

        server_proc.terminate()

        try:
            server_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_proc.kill()

    max_time = max(times)
    min_time = min(times)

    return max_time - min_time


def main():

    if len(sys.argv) != 5:
        print("Usage:")
        print("python3 test_harness.py N_list F CLIENTS MODE")
        print("Example:")
        print("python3 test_harness.py 10,20,30,40 35 4 server")
        return

    N_values = [int(x) for x in sys.argv[1].split(",")]
    F = int(sys.argv[2])
    CLIENTS = int(sys.argv[3])
    mode = sys.argv[4]

    if mode not in ("server", "client"):
        print("Mode must be 'server' or 'client'")
        return

    if os.path.exists(CSV_FILE):
        print("ERROR: CSV file already exists:", CSV_FILE)
        sys.exit(1)

    print("Experiment configuration")
    print("N values:", N_values)
    print("F:", F)
    print("Clients:", CLIENTS)
    print("Mode:", mode)
    print("Runs per experiment:", RUNS_PER_EXPERIMENT)

    with open(CSV_FILE, "w", newline="") as f:

        writer = csv.writer(f)

        for N in N_values:

            print("\n============================")
            print("Testing N =", N)
            print("============================")

            results = []

            for run in range(RUNS_PER_EXPERIMENT):

                print(f"Run {run+1}/{RUNS_PER_EXPERIMENT}")

                diff = run_experiment(N, F, CLIENTS, mode)

                results.append(diff)

                print("Difference:", diff)

            avg_diff = sum(results) / len(results)

            avg_ms = round(avg_diff * 1000, 2)

            print("Average difference (ms):", avg_ms)

            writer.writerow([N, F, avg_ms])
            f.flush()

    print("\nAll experiments complete.")
    print("Results written to", CSV_FILE)


if __name__ == "__main__":
    main()
