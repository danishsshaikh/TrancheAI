#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../apps/api"
PYTHONPATH="$PWD" python3 -m unittest discover -s tests

