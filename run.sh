#!/usr/bin/env bash
# Bootstrap and run Samaritan.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f ".venv/.deps_installed" ]; then
  pip install -q --upgrade pip
  pip install -q -r requirements.txt
  touch .venv/.deps_installed
fi

exec python -m samaritan
