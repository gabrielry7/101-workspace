#!/usr/bin/env bash
# Offline release gate. PostgreSQL must be explicitly disposable; no provider calls.
set -euo pipefail
: "${SOCIAL_TEST_DISPOSABLE_POSTGRES_URL:?Set an explicitly disposable UTF-8 PostgreSQL target}"
social_project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
export PYTHONPATH="$social_project/src${PYTHONPATH:+:$PYTHONPATH}"
"${PYTHON:-python}" -m pytest \
  "$social_project/tests/test_social_production.py" \
  "$social_project/tests/test_social_context.py" \
  "$social_project/tests/test_social_uploads.py" \
  "$social_project/tests/test_social_workspace.py" \
  "$social_project/tests/test_instagram_connections.py" \
  "$social_project/tests/test_social_workspace_browser.py" \
  --override-ini addopts='' -q "$@"
