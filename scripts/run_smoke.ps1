param(
  [string]$EnvName = "test"
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
pytest testcases/ -m smoke --env=$EnvName --alluredir=reports/allure-results

