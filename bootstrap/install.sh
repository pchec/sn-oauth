#!/usr/bin/env bash
# Bootstrap sn-oauth on macOS / Linux: ensure Python 3.8+, create a local
# virtualenv, install the package. Offers to install Python if missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

find_python() {
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then
      if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

if ! PY="$(find_python)"; then
  echo "Python 3.8+ was not found."
  if [ "$(uname)" = "Darwin" ] && command -v brew >/dev/null 2>&1; then
    read -r -p "Install Python now with Homebrew? [y/N] " ans
    if [ "${ans:-}" = "y" ] || [ "${ans:-}" = "Y" ]; then
      brew install python
    fi
  else
    echo "Please install Python 3.8+ from https://www.python.org/downloads/ and re-run this script."
    exit 1
  fi
  PY="$(find_python)" || { echo "Python still not found after install. Aborting."; exit 1; }
fi

echo "Using Python: $("$PY" --version 2>&1)"
"$PY" -m venv .venv

# A Windows venv puts the interpreter in Scripts/python.exe; a POSIX venv uses
# bin/python. Use whichever this venv created.
if [ -f ".venv/Scripts/python.exe" ]; then
  VENV_PY=".venv/Scripts/python.exe"
else
  VENV_PY=".venv/bin/python"
fi
"$VENV_PY" -m pip install --upgrade pip >/dev/null
"$VENV_PY" -m pip install -e .
echo
echo "Installed. Next:"
echo "  1) cp sn-oauth.example.json sn-oauth.json   and fill in your instance + client_id"
echo "  2) ./sn-oauth login"
