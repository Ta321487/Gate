# Detect duplicate uvicorn backends for this repo.
# Keep newest one; with -All kill every match.
# Called by kill-dup-backend.bat

param(
    [switch]$All
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$needle = "uvicorn app.main:app"
$port = 8000

# Match by command line (repo path / common name / bare app.main) OR by listeners on GF_PORT
$byCmd = @(
    Get-CimInstance Win32_Process |
        Where-Object {
            $_.Name -match '^(python|pythonw)(\.exe)?$' -and
            $_.CommandLine -and
            $_.CommandLine -like "*$needle*"
        }
)

$listenPids = @()
try {
    $listenPids = @(
        Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
} catch {}

$byPort = @()
if ($listenPids.Count -gt 0) {
    $byPort = @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $listenPids -contains $_.ProcessId -and
                $_.Name -match '^(python|pythonw)(\.exe)?$'
            }
    )
}

$merged = @{}
foreach ($p in ($byCmd + $byPort)) {
    if (-not $merged.ContainsKey($p.ProcessId)) {
        $merged[$p.ProcessId] = $p
    }
}
$procs = @($merged.Values | Sort-Object CreationDate)

if ($procs.Count -eq 0) {
    Write-Host "[ok] no uvicorn backend for this repo"
    exit 0
}

Write-Host ("[info] found {0} backend process(es):" -f $procs.Count)
foreach ($p in $procs) {
    $cmd = if ($p.CommandLine) { ($p.CommandLine -replace "\s+", " ") } else { "(no cmdline)" }
    if ($cmd.Length -gt 120) { $cmd = $cmd.Substring(0, 120) + "..." }
    Write-Host ("  pid={0}  {1}" -f $p.ProcessId, $cmd)
}

if (-not $All -and $procs.Count -le 1) {
    Write-Host "[ok] no duplicate, nothing to do"
    exit 0
}

if ($All) {
    $victims = $procs
    $kept = $null
} else {
    $victims = $procs[0..($procs.Count - 2)]
    $kept = $procs[-1]
}

foreach ($p in $victims) {
    try {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop
        Write-Host ("[kill] pid={0}" -f $p.ProcessId)
    } catch {
        Write-Host ("[warn] failed to kill pid={0}: {1}" -f $p.ProcessId, $_.Exception.Message)
    }
}

if ($kept) {
    Write-Host ("[keep] pid={0} (newest)" -f $kept.ProcessId)
} else {
    Write-Host "[ok] all cleaned"
}