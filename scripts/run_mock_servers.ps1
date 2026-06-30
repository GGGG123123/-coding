param(
  [int]$BackendPort = 9000,
  [int]$MockDevicePort = 8001
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = "$projectRoot;$env:PYTHONPATH"
$env:ADMIN_API = "http://127.0.0.1:$BackendPort"
$env:MOCK_DEVICE_CALLBACK_TOKEN = "mock-device-secret"

Start-Process -FilePath python -ArgumentList "-m uvicorn mock_server.demo_admin_backend:app --host 127.0.0.1 --port $BackendPort --reload" -WorkingDirectory $projectRoot -WindowStyle Hidden
Start-Process -FilePath python -ArgumentList "-m uvicorn mock_server.mock_device_server:app --host 127.0.0.1 --port $MockDevicePort --reload" -WorkingDirectory $projectRoot -WindowStyle Hidden

Write-Host "Demo backend: http://127.0.0.1:$BackendPort"
Write-Host "Mock device:  http://127.0.0.1:$MockDevicePort"

