import os
import sys
import socket
import threading

def start_forwarder(from_port: int, to_port: int):
    """Binds a lightweight bidirectional TCP pipe from from_port to to_port."""
    def forward_loop():
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind(("0.0.0.0", from_port))
            server.listen(25)
            print(f"[PortForwarder] Listening on {from_port} and forwarding to {to_port}", flush=True)
            while True:
                client_sock, _ = server.accept()
                def handle_client(c):
                    try:
                        target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        target.connect(("127.0.0.1", to_port))
                        def pipe(s1, s2):
                            try:
                                while True:
                                    data = s1.recv(4096)
                                    if not data:
                                        break
                                    s2.sendall(data)
                            except Exception:
                                pass
                            finally:
                                try: s1.close()
                                except: pass
                                try: s2.close()
                                except: pass

                        t1 = threading.Thread(target=pipe, args=(c, target), daemon=True)
                        t2 = threading.Thread(target=pipe, args=(target, c), daemon=True)
                        t1.start()
                        t2.start()
                    except Exception:
                        c.close()

                threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
        except Exception as e:
            print(f"[PortForwarder] Port {from_port} forwarding note: {e}", flush=True)

    threading.Thread(target=forward_loop, daemon=True).start()


def main():
    port_str = os.environ.get("PORT", "8080")
    try:
        active_port = int(port_str)
    except ValueError:
        active_port = 8080

    # Ensure both common Railway ports (8080 and 8000) are responsive
    if active_port == 8080:
        start_forwarder(from_port=8000, to_port=8080)
    elif active_port == 8000:
        start_forwarder(from_port=8080, to_port=8000)

    print(f"[MiniCAP] Launching Uvicorn on 0.0.0.0:{active_port}...", flush=True)
    import uvicorn
    uvicorn.run("src.app:app", host="0.0.0.0", port=active_port)


if __name__ == "__main__":
    main()
