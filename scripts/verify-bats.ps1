# Verify .bat files are ASCII-safe (no UTF-8 BOM, no non-ASCII bytes).
# Run: scripts\verify-bats.bat  or  powershell -File scripts\verify-bats.ps1

param(
    [switch]$Fix
)

$ErrorActionPreference = "Stop"
$Scripts = $PSScriptRoot
$bad = @()

Get-ChildItem -Path $Scripts -Filter "*.bat" | ForEach-Object {
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $issues = @()

    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $issues += "UTF-8 BOM (cmd will break @echo / if)"
    }

    foreach ($b in $bytes) {
        if ($b -gt 0x7F) {
            $issues += "non-ASCII byte 0x{0:X2}" -f $b
            break
        }
    }

    if ($issues.Count -gt 0) {
        $bad += [PSCustomObject]@{
            File = $_.Name
            Issues = ($issues -join "; ")
        }
    }
}

if ($bad.Count -eq 0) {
    Write-Host "[ok] all .bat files are ASCII-safe"
    exit 0
}

Write-Host "[FAIL] unsafe .bat files:" -ForegroundColor Red
$bad | Format-Table -AutoSize
Write-Host "Fix: keep .bat ASCII-only; put Chinese in .ps1 (UTF-8 BOM)." -ForegroundColor Yellow
exit 1
