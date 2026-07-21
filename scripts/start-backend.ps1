# Start Gate backend with owned PID (venv). Called by start-backend.bat / launcher.
# Save as UTF-8 with BOM for Windows PowerShell 5.1

param(
    [switch]$NoWait
)

$ErrorActionPreference = "Stop"
$Scripts = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Scripts "..")).Path
. (Join-Path $Scripts "_backend-procs.ps1")

function Wait-Key {
    Write-Host ""
    Write-Host "Press Enter to close..." -ForegroundColor DarkGray
    [void][Console]::ReadLine()
}

$py = Get-GfBackendVenvPython -RepoRoot $Repo
if (-not (Test-Path -LiteralPath (Join-Path $Repo "backend\app\main.py"))) {
    Write-Host "[ERROR] missing backend\app\main.py" -ForegroundColor Red
    if (-not $NoWait) { Wait-Key }
    exit 1
}
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "[ERROR] missing backend\.venv - create venv and install deps first" -ForegroundColor Red
    if (-not $NoWait) { Wait-Key }
    exit 1
}

Write-Host "[info] cleaning old uvicorn ..." -ForegroundColor DarkGray
& (Join-Path $Scripts "kill-dup-backend.ps1") -All

$deadline = (Get-Date).AddSeconds(15)
while ((Get-Date) -lt $deadline) {
    $listen = @(Get-GfListenPids -Port $script:GfBackendPort)
    if ($listen.Count -eq 0) { break }
    Start-Sleep -Milliseconds 300
}
if (@(Get-GfListenPids -Port $script:GfBackendPort).Count -gt 0) {
    Write-Host "[ERROR] port $($script:GfBackendPort) still busy" -ForegroundColor Red
    if (-not $NoWait) { Wait-Key }
    exit 1
}

Write-Host "Gate API - http://127.0.0.1:$($script:GfBackendPort)" -ForegroundColor Cyan
$proc = Start-GfBackendProcess -RepoRoot $Repo -Port $script:GfBackendPort
Write-Host ("[ok] started venv uvicorn pid={0}" -f $proc.Id) -ForegroundColor Green

if ($NoWait) {
    exit 0
}

try {
    Wait-Process -Id $proc.Id
} catch {}
Write-Host "[info] backend process exited" -ForegroundColor DarkGray
Wait-Key