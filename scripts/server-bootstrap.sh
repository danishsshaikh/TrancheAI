#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${BOOTSTRAP_ADMIN_EMAIL:-}" || -z "${BOOTSTRAP_ADMIN_PASSWORD:-}" ]]; then
  echo "Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD before running bootstrap." >&2
  exit 1
fi

cd apps/api
alembic upgrade head
python -m app.cli
