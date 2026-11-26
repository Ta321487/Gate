# Verify the scripts/ encoding contract:
#   .bat : pure ASCII, no BOM   (cmd reads GBK; BOM / non-ASCII breaks @echo and if)
#   .ps1 : UTF-8 **with BOM**   (Windows PowerShell 5.1 reads BOM-less UTF-8 as GBK,
#                                and a CJK string can then swallow its closing quote)
# Contract doc: scripts\README.md  (编码 section)
# Run: scripts\verify-scripts.bat    or    powershell -File scripts\verify-scripts.ps1
#   -Fix      auto-fix where possible: strip BOM from .bat, add BOM to .ps1
#   -NoParse  skip the Windows PowerShell 5.1 parse check

param(
    [switch]$Fix,
    [switch]$NoParse
)

$ErrorActionPreference = "Stop"
$Scripts = $PSScriptRoot
$Utf8Bom = New-Object System.Text.UTF8Encoding $true

function Test-Utf8Bom {
    param([byte[]]$Bytes)
    return ($Bytes.Length -ge 3 -and $Bytes[0] -eq 0xEF -and $Bytes[1] -eq 0xBB -and $Bytes[2] -eq 0xBF)
}

function Get-WinPsExe {
    $exe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path $exe) { return $exe }
    return $null
}

# 返回 "行:列" 列表；没有 5.1 时返回 $null（只做编码检查）
function Get-ParseErrorPositions {
    param([string]$Path)

    if ($PSVersionTable.PSVersion.Major -lt 6) {
        $tokens = $null; $errors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
        return @($errors | ForEach-Object { "$($_.Extent.StartLineNumber):$($_.Extent.StartColumnNumber)" })
    }

    $exe = Get-WinPsExe
    if (-not $exe) { return $null }

    $quoted = $Path.Replace("'", "''")
    $payload = '$t=$null;$e=$null;' +
        "[void][System.Management.Automation.Language.Parser]::ParseFile('$quoted',[ref]`$t,[ref]`$e);" +
        'foreach ($x in $e) { "" + $x.Extent.StartLineNumber + ":" + $x.Extent.StartColumnNumber }'
    $raw = @(& $exe -NoProfile -NonInteractive -Command $payload 2>&1)
    return @($raw | Where-Object { "$_" -match '^\d+:\d+$' })
}

function Repair-Encoding {
    param([System.IO.FileInfo]$File, [string]$Kind)

    if ($Kind -eq 'ps1') {
        $text = [System.IO.File]::ReadAllText($File.FullName)
        [System.IO.File]::WriteAllText($File.FullName, $text, $Utf8Bom)
        return
    }

    # .bat：去掉 BOM，字节原样保留
    $bytes = [System.IO.File]::ReadAllBytes($File.FullName)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $trimmed = New-Object byte[] ($bytes.Length - 3)
        [Array]::Copy($bytes, 3, $trimmed, 0, $trimmed.Length)
        [System.IO.File]::WriteAllBytes($File.FullName, $trimmed)
    }
}

function Get-Issues {
    param([System.IO.FileInfo]$File)

    $kind = $File.Extension.ToLowerInvariant()
    $bytes = [System.IO.File]::ReadAllBytes($File.FullName)
    $issues = @()

    if ($kind -eq '.bat') {
        if (Test-Utf8Bom $bytes) { $issues += 'UTF-8 BOM（cmd 会把 @echo / if 读坏）' }
        $bad = @($bytes | Where-Object { $_ -gt 0x7F })
        if ($bad.Count -gt 0) {
            $issues += ("非 ASCII 字节 0x{0:X2}（{1} 处）" -f $bad[0], $bad.Count)
        }
        return $issues
    }

    # .ps1
    if (-not (Test-Utf8Bom $bytes)) {
        $issues += '缺 UTF-8 BOM（PowerShell 5.1 会按 GBK 解码）'
    }
    if (-not $NoParse) {
        $pos = Get-ParseErrorPositions $File.FullName
        if ($null -ne $pos -and $pos.Count -gt 0) {
            $head = ($pos | Select-Object -First 3) -join ', '
            $issues += "PowerShell 5.1 解析失败 $($pos.Count) 处（首处 $head）"
        }
    }
    return $issues
}

$files = @(Get-ChildItem -LiteralPath $Scripts -File |
    Where-Object { $_.Extension -in @('.bat', '.ps1') })

$bad = @()
foreach ($f in $files) {
    $issues = @(Get-Issues $f)
    if ($issues.Count -eq 0) { continue }

    if ($Fix) {
        if ($f.Extension -eq '.ps1') { Repair-Encoding $f 'ps1' }
        else { Repair-Encoding $f 'bat' }
        $issues = @(Get-Issues $f)
        if ($issues.Count -eq 0) {
            Write-Host ("[fix] {0}" -f $f.Name) -ForegroundColor Green
            continue
        }
        $issues = @('Fix 后仍有问题：' + ($issues -join '; '))
    }

    $bad += [PSCustomObject]@{
        File   = $f.Name
        Issues = ($issues -join '; ')
    }
}

if ($bad.Count -eq 0) {
    Write-Host ("[ok] {0} 个 .bat / .ps1 符合编码约定" -f $files.Count) -ForegroundColor Green
    exit 0
}

Write-Host "[FAIL] 编码不符合约定的脚本：" -ForegroundColor Red
Write-Host (($bad | Format-Table -AutoSize -Wrap | Out-String).TrimEnd()) -ForegroundColor Red
Write-Host "约定：.bat 纯 ASCII 无 BOM；.ps1 UTF-8 with BOM（见 scripts\README.md）" -ForegroundColor Yellow
Write-Host "可自动修的用 -Fix：" -ForegroundColor Yellow
Write-Host "  powershell -File scripts\verify-scripts.ps1 -Fix" -ForegroundColor Yellow
exit 1
