#!/bin/sh
set -eu
cd "$(dirname "$0")/../backend"
export HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false
exec ../.venv/bin/python -m brain
