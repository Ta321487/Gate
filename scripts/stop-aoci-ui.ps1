Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Info([string]$Message, [string]$Icon = "Information") {
  Add-Type -AssemblyName System.Windows.Forms | Out-Null
  $iconValue = [System.Windows.Forms.MessageBoxIcon]::$Icon
  [System.Windows.Forms.MessageBox]::Show(
    $Message,
    "AOCI panel",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    $iconValue
  ) | Out-Null
}

$Aoci = "C:\Users\17386\tools\aoci\aoci.exe"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not (Test-Path $Aoci)) {
  Show-Info "找不到 aoci：`n$Aoci" "Error"
  exit 1
}

try {
  & $Aoci --repo $Repo ui --stop | Out-Null
} catch {
  Show-Info "停止失败：`n$($_.Exception.Message)" "Error"
  exit 1
}
exit 0