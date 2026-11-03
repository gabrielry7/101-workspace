#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${CAMPAIGN_PYTHON:-python3}" -m world_model.restaurant_commerce.campaign_demo "$@"
