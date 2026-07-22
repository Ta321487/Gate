param()
$ErrorActionPreference = "Continue"
try { chcp 65001 | Out-Null } catch {}
. (Join-Path $PSScriptRoot "_backend-procs.ps1")
$port = 5173
$ids = @(
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
)
if ($ids.Count -eq 0) {
    Write-Host "[ok] 前端未在监听 :$port"
    exit 0
}
foreach ($id in $ids) {
    $r = Stop-GfProcessTree -ProcessId ([int]$id)
    if ($r.ok) {
        Write-Host "[kill] 前端 pid=$id"
    } else {
        Write-Host ("[warn] 无法结束 pid={0}: {1}" -f $id, $r.message)
    }
}