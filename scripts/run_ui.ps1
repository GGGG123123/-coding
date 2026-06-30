param(
  [string]$EnvName = "pre",
  [switch]$Headed
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if ($Headed) {
  pytest ui_cases/ --env=$EnvName --run-ui --headed --alluredir=reports/allure-results
} else {
  pytest ui_cases/ --env=$EnvName --run-ui --alluredir=reports/allure-results
}

