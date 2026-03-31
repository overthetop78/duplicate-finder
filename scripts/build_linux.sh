#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! "$PYTHON_BIN" -m pip --version >/dev/null 2>&1; then
  if /usr/bin/python3 -m pip --version >/dev/null 2>&1; then
    PYTHON_BIN="/usr/bin/python3"
  else
    "$PYTHON_BIN" -m ensurepip --upgrade
  fi
fi

echo "[1/3] Installation des dependances de build"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r requirements.txt -r requirements-build.txt

echo "[2/3] Nettoyage"
rm -rf build dist

echo "[3/3] Build Linux autonome (onefile)"
"$PYTHON_BIN" -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --onefile \
  --name duplicate-finder \
  --hidden-import openpyxl \
  --hidden-import xlrd \
  --hidden-import odf \
  --hidden-import pandas \
  src/main.py

echo "Build termine: dist/duplicate-finder"
