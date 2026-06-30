#!/usr/bin/env bash
set -euo pipefail
ENV_NAME="${1:-test}"
cd "$(dirname "$0")/.."

rm -rf reports/allure-results
mkdir -p reports/allure-results

python -m pytest testcases/ --env="$ENV_NAME" --alluredir=reports/allure-results
python -m ai_assistant.analyze_results --results reports/allure-results --output reports/ai-analysis-report.md

echo "AI analysis report: reports/ai-analysis-report.md"

