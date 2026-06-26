#!/usr/bin/env bash
# dev.sh — LynxMask Desktop
# Uruchamia backend Python + Tauri dev (hot-reload).
# Odpowiednik "Run" z Android Studio — do codziennego dewelopmentu.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_DIR="$SCRIPT_DIR/backend"

echo "=== LynxMask Desktop — Dev ==="

# ── Backend Python ─────────────────────────────────────────────────────────────
echo ""
echo "[1/3] Uruchamiam backend (port 8765)..."
cd "$BACKEND_DIR"
python3 pseudominizer_api.py &
BACKEND_PID=$!
echo "      PID=$BACKEND_PID"

# Poczekaj aż backend odpowie
for i in $(seq 1 15); do
    if curl -sf http://127.0.0.1:8765/health > /dev/null 2>&1; then
        echo "      Backend gotowy."
        break
    fi
    sleep 1
    if [ $i -eq 15 ]; then
        echo "      UWAGA: backend nie odpowiedział po 15s — sprawdź logi."
    fi
done

# ── Zależności JS ──────────────────────────────────────────────────────────────
echo "[2/3] npm install..."
cd "$FRONTEND_DIR"
npm install --silent

# ── Tauri dev ─────────────────────────────────────────────────────────────────
echo "[3/3] cargo tauri dev (hot-reload)..."
npm run tauri dev

# Sprzątanie po zamknięciu okna
echo ""
echo "Zatrzymuję backend (PID=$BACKEND_PID)..."
kill "$BACKEND_PID" 2>/dev/null || true
