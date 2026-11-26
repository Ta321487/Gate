# Deprecated alias. The real gate is verify-scripts.ps1 (covers .bat + .ps1).
# Kept because scripts\README.md, launcher menu V and older notes call verify-bats.bat.
# Run: scripts\verify-bats.bat   ->   scripts\verify-scripts.bat

param(
    [switch]$Fix
)

& (Join-Path $PSScriptRoot "verify-scripts.ps1") -Fix:$Fix
exit $LASTEXITCODE
