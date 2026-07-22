# Detect duplicate uvicorn backends for this repo.
# Keep listening process tree (venv parent + child); with -All kill every match.
# Called by kill-dup-backend.bat

param(
    [switch]$All
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "_backend-procs.ps1")
$port = $script:GfBackendPort

$info = Get-GfBackendProcs -Port $port
$procs = @($info.Procs)
$listenPids = @($info.ListenPids)

if ($procs.Count -eq 0) {
    Write-Host "[ok] no uvicorn backend for this repo"
    exit 0
}

Write-Host ("[info] found {0} backend process(es):" -f $procs.Count)
foreach ($p in $procs) {
    $cmd = if ($p.CommandLine) { ($p.CommandLine -replace "\s+", " ") } else { "(no cmdline)" }
    if ($cmd.Length -gt 120) { $cmd = $cmd.Substring(0, 120) + "..." }
    $mark = if ($listenPids -contains $p.ProcessId) { " [listening :$port]" } else { " [not listening]" }
    Write-Host ("  pid={0}{1}  {2}" -f $p.ProcessId, $mark, $cmd)
}

$protected = Get-GfProtectedBackendPids -ListenPids $listenPids
# One venv tree = launcher parent + listening child → not a "duplicate"
$foreign = @($procs | Where-Object { -not $protected.ContainsKey([int]$_.ProcessId) })

if (-not $All) {
    if ($listenPids.Count -ge 1 -and $foreign.Count -eq 0) {
        Write-Host "[ok] single backend tree (venv parent+child), nothing to kill"
        exit 0
    }
    if ($procs.Count -le 1) {
        Write-Host "[ok] no duplicate, nothing to do"
        exit 0
    }
}

if ($All) {
    $victimIds = @($procs | ForEach-Object { [int]$_.ProcessId })
    $keptLabel = $null
} else {
    $victimIds = @($foreign | ForEach-Object { [int]$_.ProcessId })
    $keptLabel = ($listenPids -join ",")
}

# Only kill tree roots — venv child (home python.exe) often Access Denied if killed alone
$roots = @(Get-GfTreeRootPids -ProcessIds $victimIds)
foreach ($id in $roots) {
    $r = Stop-GfProcessTree -ProcessId $id
    if ($r.ok) {
        Write-Host ("[kill] pid={0}" -f $id)
    } else {
        Write-Host ("[warn] failed to kill pid={0}: {1}" -f $id, $r.message)
    }
}

if ($All) {
    Write-Host "[ok] all cleaned"
} elseif ($roots.Count -eq 0) {
    Write-Host "[ok] nothing to kill"
} else {
    Write-Host ("[keep] listening tree pid(s)={0}" -f $keptLabel)
}
