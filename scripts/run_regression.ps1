param(
  [string]$EnvName = "test"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
pytest testcases/ --env=$EnvName --alluredir=reports/allure-results

