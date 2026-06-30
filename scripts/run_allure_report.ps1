param(
  [string]$EnvName = "test"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$javaHome = $env:JAVA_HOME
if (-not $javaHome) {
  $javaHome = [Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
}
if (-not $javaHome) {
  $javaHome = [Environment]::GetEnvironmentVariable("JAVA_HOME", "Machine")
}
if ($javaHome -and (Test-Path (Join-Path $javaHome "bin\java.exe"))) {
  $env:JAVA_HOME = $javaHome
  $javaBin = Join-Path $javaHome "bin"
  if (($env:Path -split ";") -notcontains $javaBin) {
    $env:Path = "$javaBin;$env:Path"
  }
}

if (Test-Path "reports/allure-results") {
  Remove-Item -LiteralPath "reports/allure-results" -Recurse -Force
}
New-Item -ItemType Directory -Force -Path "reports/allure-results" | Out-Null

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  & $venvPython -m pytest testcases/ --env=$EnvName --alluredir=reports/allure-results
} else {
  python -m pytest testcases/ --env=$EnvName --alluredir=reports/allure-results
}

$allure = Get-Command allure -ErrorAction SilentlyContinue
if ($allure) {
  allure serve reports/allure-results
  exit 0
}

$npx = Get-Command npx -ErrorAction SilentlyContinue
if ($npx) {
  npx --yes allure-commandline serve reports/allure-results
  exit 0
}

Write-Host "Allure result files were generated in reports/allure-results."
Write-Host "Install Allure CLI or Node.js, then run: allure serve reports/allure-results"
