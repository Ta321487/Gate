param()
$ErrorActionPreference = "Continue"
try { chcp 65001 | Out-Null } catch {}
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
    try {
        Stop-Process -Id $id -Force -ErrorAction Stop
        Write-Host "[kill] 前端 pid=$id"
    } catch {
        Write-Host "[warn] 无法结束 pid=$id"
    }
}