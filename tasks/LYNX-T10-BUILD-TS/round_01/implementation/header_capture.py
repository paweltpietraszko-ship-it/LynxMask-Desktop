#!/usr/bin/env python3
"""
LYNX-T10 — pomiar rzeczywistych nagłówków Origin/Host z wydania Tauri wobec backendu T02.
Artefakt testowy (NIE kod produktu): uruchamia `pseudominizer_api.app` z podanego katalogu backendu (worktree T02
`dc498366…`) opakowane zewnętrznym ASGI-wrapperem, który zapisuje do pliku JSONL wyłącznie:
metoda, ścieżka, Origin, Host, czy był nagłówek X-Api-Token (bool, nie wartość), status odpowiedzi.
Bez treści żądań/odpowiedzi i bez tokenów. Profil/archiwum: tymczasowe (env ustawia wywołujący).
Po starcie kopiuje wygenerowany token do --token-copy (miejsce, z którego czyta go aplikacja Tauri).

Użycie: py -3 header_capture.py --backend <worktree_T02>/backend --log naglowki.jsonl --token-copy <repo>/backend/api_token.txt
"""
import argparse
import json
import os
import shutil
import sys
import threading
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument("--token-copy", required=True)
    args = ap.parse_args()
    backend = os.path.abspath(args.backend)
    sys.path.insert(0, backend)
    os.chdir(backend)
    import uvicorn
    import pseudominizer_api as api

    log = open(args.log, "a", encoding="utf-8")

    async def capture(scope, receive, send):
        if scope["type"] != "http":
            return await api.app(scope, receive, send)
        h = {k.decode().lower(): v.decode() for k, v in scope["headers"]}
        rec = {"t": round(time.time(), 3), "method": scope["method"], "path": scope["path"],
               "origin": h.get("origin"), "host": h.get("host"), "has_token": "x-api-token" in h}

        async def send_wrap(msg):
            if msg["type"] == "http.response.start":
                rec["status"] = msg["status"]
                log.write(json.dumps(rec) + "\n")
                log.flush()
            await send(msg)
        return await api.app(scope, receive, send_wrap)

    def copy_token():
        src = os.path.join(backend, "api_token.txt")
        for _ in range(120):
            if os.path.exists(src) and os.path.getsize(src) > 0:
                shutil.copyfile(src, args.token_copy)
                print("[capture] token skopiowany", flush=True)
                return
            time.sleep(0.5)
        print("[capture] brak api_token.txt po 60 s", flush=True)

    threading.Thread(target=copy_token, daemon=True).start()
    uvicorn.run(capture, host="127.0.0.1", port=8765, log_level="warning", lifespan="on")


if __name__ == "__main__":
    main()
