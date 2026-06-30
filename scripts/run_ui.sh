#!/usr/bin/env bash
set -euo pipefail
ENV_NAME="${1:-pre}"
cd "$(dirname "$0")/.."
pytest ui_cases/ --env="$ENV_NAME" --run-ui --alluredir=reports/allure-results

