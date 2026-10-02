#!/usr/bin/env bash
# Prepare an isolated local E2E database. The password below is for the temporary example container only.
set -euo pipefail

backend_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$backend_dir"

export DATABASE_URL="${E2E_DATABASE_URL:-postgresql+psycopg://postgres:pw@localhost:55432/orbit_t}"
"$backend_dir/.venv/bin/alembic" upgrade head
"$backend_dir/.venv/bin/python" -m app.seed --default-users
