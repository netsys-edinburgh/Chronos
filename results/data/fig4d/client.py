import socket
import sys
import time


PORT = 5000


def fib(n):
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)


def run_server_mode(N, F, server_ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((server_ip, PORT))

    f = s.makefile("r")

    # Send hello
    s.sendall(b"hello\n")

    start_time = None

    for i in range(N):

        # Wait for begin
        msg = f.readline().strip()
        if msg != "begin":
            print("Unexpected message:", msg)
            return

        if start_time is None:
            start_time = time.time()

        fib(F)

        # Send done
        s.sendall(b"done\n")

    end_time = time.time()

    print(f"Elapsed time: {end_time - start_time:.4f} seconds")

    s.close()


def run_serverless_mode(N, F):
    start_time = None

    for i in range(N):
        if start_time is None:
            start_time = time.time()

        fib(F)

    end_time = time.time()

    print(f"Elapsed time: {end_time - start_time:.4f} seconds")


def main():
    if len(sys.argv) not in (3, 4):
        print("Usage: python client.py N F [server_ip]")
        return

    N = int(sys.argv[1])
    F = int(sys.argv[2])

    if len(sys.argv) == 4:
        server_ip = sys.argv[3]
        run_server_mode(N, F, server_ip)
    else:
        run_serverless_mode(N, F)


if __name__ == "__main__":
    main()