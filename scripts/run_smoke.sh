#!/usr/bin/env bash
set -euo pipefail
ENV_NAME="${1:-test}"
cd "$(dirname "$0")/.."
pytest testcases/ -m smoke --env="$ENV_NAME" --alluredir=reports/allure-results

