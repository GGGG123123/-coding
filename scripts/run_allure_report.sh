#!/usr/bin/env bash
set -euo pipefail
ENV_NAME="${1:-test}"
cd "$(dirname "$0")/.."

rm -rf reports/allure-results
mkdir -p reports/allure-results

pytest testcases/ --env="$ENV_NAME" --alluredir=reports/allure-results

if command -v allure >/dev/null 2>&1; then
  allure serve reports/allure-results
elif command -v npx >/dev/null 2>&1; then
  npx --yes allure-commandline serve reports/allure-results
else
  echo "Allure result files were generated in reports/allure-results."
  echo "Install Allure CLI or Node.js, then run: allure serve reports/allure-results"
fi
