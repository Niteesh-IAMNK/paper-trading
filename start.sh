#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -f "venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  PYTHON=python
fi

"$PYTHON" app_runner.py
