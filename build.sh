#!/usr/bin/env bash
# build.sh — LynxMask Desktop
# Odpowiednik "Build > Build Bundle/APK" z Android Studio.
# Buduje release: frontend (npm) + Tauri (cargo).
# Nie uruchamia backendu — backend to osobny proces (dev.sh).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "=== LynxMask Desktop — Build ==="

# ── 1. Zależności JS ──────────────────────────────────────────────────────────
echo ""
echo "[1/3] npm install..."
cd "$FRONTEND_DIR"
npm install --silent

# ── 2. TypeScript + Vite ──────────────────────────────────────────────────────
echo "[2/3] npm run build (tsc + vite)..."
npm run build

# ── 3. Tauri release ──────────────────────────────────────────────────────────
echo "[3/3] cargo tauri build..."
npm run tauri build

echo ""
echo "✓ Build gotowy."
echo "  Instalator: frontend/src-tauri/target/release/bundle/"
