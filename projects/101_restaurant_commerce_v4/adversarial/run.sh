#!/usr/bin/env bash
# One entry point. Needs uv, PostgreSQL tools, Node/npm and Chromium on PATH.
set -euo pipefail
cd "$(dirname "$0")/.."
export COMMERCE_TOOLCHAIN="${COMMERCE_TOOLCHAIN:-/tmp/101-commerce-toolchain}"
mkdir -p "$COMMERCE_TOOLCHAIN"
for executable in uv initdb pg_ctl createdb node npm chromium; do
  command -v "$executable" >/dev/null || { echo "BLOCKED: missing prerequisite $executable" >&2; exit 2; }
done
if [ ! -x "$COMMERCE_TOOLCHAIN/venv/bin/python" ]; then
  uv venv --python 3.12 "$COMMERCE_TOOLCHAIN/venv"
fi
uv pip install --python "$COMMERCE_TOOLCHAIN/venv/bin/python" -r adversarial/requirements-tools.txt
"$COMMERCE_TOOLCHAIN/venv/bin/python" -m ensurepip --upgrade >/dev/null
"$COMMERCE_TOOLCHAIN/venv/bin/python" adversarial/bootstrap.py
exec "$COMMERCE_TOOLCHAIN/venv/bin/python" adversarial/run.py "$@"
