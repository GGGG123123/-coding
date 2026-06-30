param(
  [string]$EnvName = "test"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
pytest testcases/test_ota.py --env=$EnvName --alluredir=reports/allure-results

