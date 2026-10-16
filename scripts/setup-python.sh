#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
.venv/bin/python backend/experiments/download_models.py
printf 'Python engine ready. Run scripts/start-backend.sh or rebuild and open the Mac app.\n'
