param(
  [string]$EnvName = "test"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

function Import-UserEnv {
  param([string]$Name)
  if (-not [Environment]::GetEnvironmentVariable($Name, "Process")) {
    $value = [Environment]::GetEnvironmentVariable($Name, "User")
    if ($value) {
      [Environment]::SetEnvironmentVariable($Name, $value, "Process")
    }
  }
}

Import-UserEnv "DASHSCOPE_API_KEY"
Import-UserEnv "DASHSCOPE_API_BASE"
Import-UserEnv "DASHSCOPE_MODEL"
Import-UserEnv "MODEL_API_KEY"
Import-UserEnv "MODEL_API_BASE"
Import-UserEnv "MODEL_API_PATH"
Import-UserEnv "MODEL_NAME"
Import-UserEnv "LLM_API_KEY"
Import-UserEnv "LLM_API_BASE"
Import-UserEnv "LLM_API_PATH"
Import-UserEnv "LLM_API_MODEL"

if (Test-Path "reports/allure-results") {
  Remove-Item -LiteralPath "reports/allure-results" -Recurse -Force
}
New-Item -ItemType Directory -Force -Path "reports/allure-results" | Out-Null

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  & $venvPython -m pytest testcases/ --env=$EnvName --alluredir=reports/allure-results
  & $venvPython -m ai_assistant.analyze_results --results reports/allure-results --output reports/ai-analysis-report.md
} else {
  python -m pytest testcases/ --env=$EnvName --alluredir=reports/allure-results
  python -m ai_assistant.analyze_results --results reports/allure-results --output reports/ai-analysis-report.md
}

Write-Host "AI analysis report: reports/ai-analysis-report.md"
