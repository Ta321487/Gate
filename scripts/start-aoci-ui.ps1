Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Error([string]$Message) {
  Add-Type -AssemblyName System.Windows.Forms | Out-Null
  [System.Windows.Forms.MessageBox]::Show(
    $Message,
    "AOCI panel",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Error
  ) | Out-Null
}

$Aoci = "C:\Users\17386\tools\aoci\aoci.exe"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$GitShimDir = Join-Path $PSScriptRoot "aoci-git-shim"
$RealGit = "D:\Program Files\Git\mingw64\bin\git.exe"

if (-not (Test-Path $Aoci)) {
  Show-Error "找不到 aoci：`n$Aoci"
  exit 1
}

# AOCI UI polls git frequently; on Windows the console subsystem flashes a blank
# window unless CreateNoWindow is used. Prefer the WinExe shim ahead of PATH.
if ((Test-Path (Join-Path $GitShimDir "git.exe")) -and (Test-Path $RealGit)) {
  $env:AOCI_REAL_GIT = $RealGit
  $env:PATH = "$GitShimDir;$env:PATH"
}

try {
  $raw = & $Aoci --repo $Repo ui --detach --json 2>&1 | Out-String
} catch {
  Show-Error "启动失败：`n$($_.Exception.Message)"
  exit 1
}

$url = $null
if ($raw -match '"url"\s*:\s*"(http://[^"]+)"') {
  $url = $Matches[1]
} elseif ($raw -match '(http://127\.0\.0\.1:\d+/?)') {
  $url = $Matches[1]
}

if (-not $url) {
  Show-Error "面板已尝试启动，但未解析到 URL：`n$($raw.Trim())"
  exit 1
}

Start-Process $url
exit 0