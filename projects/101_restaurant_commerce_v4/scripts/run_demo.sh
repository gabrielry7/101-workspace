#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PYTHONPATH:-}:$PWD/src"
python -m world_model.restaurant_commerce.demo --db /tmp/101-restaurant-commerce-v3.db --port 8787
