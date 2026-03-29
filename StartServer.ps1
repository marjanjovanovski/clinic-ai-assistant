$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $repoRoot "clinic-ai-assistant-src\backend"
$pythonPath = Join-Path $backendPath ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $backendPath)) {
    throw "Backend directory not found: $backendPath"
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Python executable not found: $pythonPath"
}

Set-Location -LiteralPath $backendPath
& $pythonPath -m uvicorn app.main:app --reload
