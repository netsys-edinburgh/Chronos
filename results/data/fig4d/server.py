import socket
import threading

PORT = 5000

clients = []
clients_lock = threading.Lock()

done_count = 0
done_lock = threading.Lock()
done_event = threading.Event()


def client_thread(conn, addr, total_clients):
    global done_count

    f = conn.makefile("r")

    # Expect hello
    msg = f.readline().strip()
    if msg != "hello":
        print(f"Unexpected message from {addr}: {msg}")
        conn.close()
        return

    print(f"Client {addr} said hello")

    with clients_lock:
        clients.append(conn)

    # Wait for begin messages and respond with done
    while True:
        msg = f.readline()
        if not msg:
            break

        msg = msg.strip()

        if msg == "done":
            with done_lock:
                done_count += 1
                if done_count == total_clients:
                    done_event.set()

    conn.close()


def send_begin():
    with clients_lock:
        for c in clients:
            try:
                c.sendall(b"begin\n")
            except:
                pass


def main():
    import sys

    if len(sys.argv) != 2:
        print("Usage: python server.py X")
        return

    total_clients = int(sys.argv[1])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", PORT))
    s.listen()

    print(f"Server listening on port {PORT}")
    print(f"Waiting for {total_clients} clients...")

    # Accept connections
    threads = []
    while len(threads) < total_clients:
        conn, addr = s.accept()
        print(f"Connection from {addr}")

        t = threading.Thread(target=client_thread, args=(conn, addr, total_clients))
        t.daemon = True
        t.start()
        threads.append(t)

    # Wait until all hellos received
    while True:
        with clients_lock:
            if len(clients) == total_clients:
                break

    print("All clients connected. Starting computation.")

    send_begin()

    global done_count

    while True:
        done_event.wait()

        print("All clients completed iteration")

        with done_lock:
            done_count = 0
            done_event.clear()

        send_begin()


if __name__ == "__main__":
    main()