#!/usr/bin/env bash
# Offline release gate. PostgreSQL must be explicitly disposable; no provider calls.
set -euo pipefail
: "${SOCIAL_TEST_DISPOSABLE_POSTGRES_URL:?Set an explicitly disposable UTF-8 PostgreSQL target}"
social_project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export PYTHONPATH="$social_project/src${PYTHONPATH:+:$PYTHONPATH}"
"${PYTHON:-python}" "$social_project/scripts/verify_social.py" "$@"
