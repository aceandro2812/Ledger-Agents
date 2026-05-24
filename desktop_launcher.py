import os
import sys
import socket
import threading
import time
import webbrowser
import uvicorn

# Change current working directory to the executable folder if packaged.
# This ensures SQLite database, uploads, and config.json are persistent on user's disk.
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from backend.main import app


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_for_server(port: int, timeout: float = 15.0):
    """Block until the FastAPI server is accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=0.5)
            s.close()
            return True
        except OSError:
            time.sleep(0.2)
    return False


def start_backend(port: int):
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == '__main__':
    port = get_free_port()

    # Start FastAPI backend in a background daemon thread
    backend_thread = threading.Thread(target=start_backend, args=(port,), daemon=True)
    backend_thread.start()

    # Wait until the server is ready, then open the default browser
    if wait_for_server(port):
        webbrowser.open(f"http://127.0.0.1:{port}")
    else:
        print(f"[Warning] Server did not start on port {port} within 15s. Try opening manually.")

    # Keep the process alive (daemon thread dies with the main thread)
    backend_thread.join()
