#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -d "venv" ]]; then
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source "venv/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-fyers.txt --no-deps
python -m playwright install msedge

echo
echo "Dependencies installed."
