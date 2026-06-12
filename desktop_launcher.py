import os
import sys
import socket
import threading
import time
import uvicorn
import webview

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


server_instance = None

def start_backend(port: int):
    global server_instance
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server_instance = uvicorn.Server(config)
    server_instance.run()


if __name__ == '__main__':
    port = get_free_port()

    # Start FastAPI backend in a background daemon thread
    backend_thread = threading.Thread(target=start_backend, args=(port,), daemon=True)
    backend_thread.start()

    # Wait until the server is ready, then open the pywebview window
    if wait_for_server(port):
        # Create a native window frame loading our local server url
        webview.create_window(
            title="Ledger Forensic Audit",
            url=f"http://127.0.0.1:{port}",
            width=1280,
            height=800,
            min_size=(1024, 768)
        )
        # Block main thread until the webview window is closed
        webview.start()
        # Trigger graceful shutdown on uvicorn
        if server_instance:
            server_instance.should_exit = True
        time.sleep(0.5)
        # Forcefully terminate the entire process
        os._exit(0)
    else:
        print(f"[Error] FastAPI backend did not start on port {port} within 15s.")
        sys.exit(1)


