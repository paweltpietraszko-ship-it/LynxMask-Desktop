"""Real ASGI server: endpoint exception response and server log, synthetic data."""
import contextlib
import io
import logging
from pathlib import Path
import socket
import subprocess
import sys
import threading
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[4]
SHA = "8194c0d3b84f47535089ed07c98ed15a61a33a1a"
sys.path.insert(0, str(ROOT / "backend"))
MARKER = "SYNTHETIC_ENDPOINT_VALUE_44051401359"


def main():
    expected = subprocess.check_output(["git", "show", f"{SHA}:backend/pseudominizer_api.py"], cwd=ROOT).decode()
    assert (ROOT / "backend/pseudominizer_api.py").read_text(encoding="utf-8") == expected
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        import pseudominizer_api as api
        import requests
        import uvicorn
    logs = io.StringIO()
    logger = logging.getLogger("uvicorn.error")
    old = logger.handlers[:], logger.propagate, logger.level
    logger.handlers = [logging.StreamHandler(logs)]
    logger.propagate = False
    logger.setLevel(logging.ERROR)
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(api.app, lifespan="off", log_config=None, access_log=False))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    try:
        with patch.object(api, "_API_TOKEN", "a" * 64), patch.object(api, "_EXPRESS_TOKEN", "b" * 64), \
                patch.object(api, "_extract_text", side_effect=ValueError(MARKER)):
            thread.start()
            for _ in range(100):
                if server.started:
                    break
                threading.Event().wait(.05)
            assert server.started
            for path, key in (("/preview", "a" * 64), ("/preview-express", "b" * 64)):
                logs.seek(0)
                logs.truncate()
                response = requests.post(f"http://127.0.0.1:{port}{path}",
                    headers={"X-Api-Token": key, "Host": "127.0.0.1:8765"},
                    files={"file": ("synthetic.txt", b"neutral text", "text/plain")}, timeout=5)
                for _ in range(100):
                    if MARKER in logs.getvalue():
                        break
                    threading.Event().wait(.01)
                assert response.status_code == 500 and response.text == "Internal Server Error", (response.status_code, response.text[:100])
                assert MARKER not in response.text
                assert MARKER in logs.getvalue(), "expected server log disclosure not reproduced"
                print(path, "HTTP 500 text/plain; full exception value in actual ASGI server log")
    finally:
        server.should_exit = True
        if thread.is_alive():
            thread.join(timeout=5)
        sock.close()
        logger.handlers, logger.propagate, logger.level = old


if __name__ == "__main__":
    main()
