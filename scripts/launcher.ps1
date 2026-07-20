# Gate console launcher
# Entry: scripts\launcher.bat
# Save as UTF-8 with BOM (Chinese + Windows PowerShell 5.1)

$ErrorActionPreference = "Continue"

try { chcp 65001 | Out-Null } catch {}
$utf8 = New-Object System.Text.UTF8Encoding $false
[Console]::OutputEncoding = $utf8
[Console]::InputEncoding = $utf8
$OutputEncoding = $utf8
try {
    $Host.UI.RawUI.WindowTitle = "毕设港 Gate · 控制台"
} catch {}

$Scripts = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Scripts "..")).Path
$BackendPort = 8000
$FrontendPort = 5173
$UiUrl = "http://127.0.0.1:$FrontendPort"
$ApiUrl = "http://127.0.0.1:$BackendPort"
$DocsUrl = "$ApiUrl/docs"
$HealthUrl = "$ApiUrl/api/health"
$ColWidth = 26   # display columns for left menu cell (CJK-aware)

function Write-Line([string]$Text = "", [string]$Color = "Gray") {
    Write-Host $Text -ForegroundColor $Color
}

function Get-DisplayWidth([string]$Text) {
    $w = 0
    foreach ($ch in $Text.ToCharArray()) {
        if ([int][char]$ch -gt 0x7F) { $w += 2 } else { $w += 1 }
    }
    return $w
}

function Pad-Display([string]$Text, [int]$Width) {
    $pad = $Width - (Get-DisplayWidth $Text)
    if ($pad -lt 0) { return $Text }
    return ($Text + (" " * $pad))
}

function Pause-Menu([string]$Hint = "按 Enter 返回菜单...") {
    Write-Host ""
    Write-Host "  $Hint" -ForegroundColor DarkGray
    [void][Console]::ReadLine()
}

function Test-PortListening([int]$Port) {
    try {
        return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    } catch {
        return $false
    }
}

function Get-BackendProcs {
    $needle = "uvicorn app.main:app"
    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '^(python|pythonw)(\.exe)?$' -and
                $_.CommandLine -and
                $_.CommandLine -like "*$needle*"
            } |
            Sort-Object CreationDate
    )
}

function Invoke-HealthCheck {
    try {
        $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 3
        return @{ ok = $true; body = ($r | ConvertTo-Json -Compress) }
    } catch {
        return @{ ok = $false; body = $_.Exception.Message }
    }
}

function Start-InNewWindow([string]$Title, [string]$BatPath) {
    if (-not (Test-Path -LiteralPath $BatPath)) {
        Write-Line "  [错误] 找不到 $BatPath" "Red"
        return
    }
    Start-Process -FilePath "cmd.exe" -WorkingDirectory $Repo -ArgumentList @(
        "/k",
        "title $Title & call `"$BatPath`""
    ) | Out-Null
    Write-Line "  [完成] 已打开窗口：$Title" "Green"
}

function Invoke-LocalBat([string]$BatPath, [string[]]$BatArgs = @()) {
    if (-not (Test-Path -LiteralPath $BatPath)) {
        Write-Line "  [错误] 找不到 $BatPath" "Red"
        return
    }
    & cmd.exe /c "call `"$BatPath`" $($BatArgs -join ' ')"
}

function Stop-BackendAll {
    Invoke-LocalBat (Join-Path $Scripts "stop-backend.bat")
}

function Stop-FrontendAll {
    Invoke-LocalBat (Join-Path $Scripts "stop-frontend.bat")
}

function Open-PathOrUrl([string]$Target) {
    try {
        Start-Process $Target | Out-Null
        Write-Line "  [完成] 已打开 $Target" "Green"
    } catch {
        Write-Line "  [错误] $($_.Exception.Message)" "Red"
    }
}

function Test-DockerCli {
    return [bool](Get-Command docker -ErrorAction SilentlyContinue)
}

function Invoke-Docker([string[]]$ComposeArgs) {
    $compose = Join-Path $Repo "docker-compose.yml"
    if (-not (Test-Path $compose)) {
        Write-Line "  [错误] 找不到 docker-compose.yml" "Red"
        return
    }
    if (-not (Test-DockerCli)) {
        Write-Line "  [错误] 未找到 docker 命令（需要 Docker Desktop）" "Red"
        Write-Line "  说明：这里管的是仓库 docker-compose.yml 里的 MySQL 容器，" "DarkGray"
        Write-Line "        不是 Windows 本机的 MySQL80 服务。" "DarkGray"
        return
    }
    Push-Location $Repo
    try {
        Write-Line ("  > docker compose {0}" -f ($ComposeArgs -join " ")) "DarkGray"
        Write-Line "  （Compose 容器，非本机 MySQL80）" "DarkGray"
        & docker compose @ComposeArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Line "  [警告] docker 退出码 $LASTEXITCODE" "Yellow"
        }
    } catch {
        Write-Line "  [错误] $($_.Exception.Message)" "Red"
        Write-Line "  请确认 Docker Desktop 已安装并正在运行" "DarkGray"
    } finally {
        Pop-Location
    }
}

# --- layout ------------------------------------------------------------------

function Write-Cell([string]$Key, [string]$Label, [string]$Color, [switch]$NoNewline) {
    $cell = Pad-Display ("[$Key] $Label") $ColWidth
    if ($NoNewline) {
        Write-Host "  $cell" -NoNewline -ForegroundColor $Color
    } else {
        Write-Host "  $cell" -ForegroundColor $Color
    }
}

function Write-Pair(
    [string]$K1, [string]$L1,
    [string]$K2 = "", [string]$L2 = "",
    [string]$C1 = "Gray", [string]$C2 = "Gray"
) {
    Write-Cell $K1 $L1 $C1 -NoNewline
    if ($K2) {
        Write-Host ("[$K2] $L2") -ForegroundColor $C2
    } else {
        Write-Host ""
    }
}

function Write-BlockTitle([string]$Title) {
    Write-Host ""
    Write-Host "  $Title" -ForegroundColor Cyan
}

function Show-StatusStrip {
    $beUp = Test-PortListening $BackendPort
    $feUp = Test-PortListening $FrontendPort
    $beProcs = Get-BackendProcs

    Write-Host ""
    Write-Host "  " -NoNewline
    Write-Host "后端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $BackendPort) -NoNewline -ForegroundColor DarkGray
    if ($beUp) { Write-Host "ON " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    else { Write-Host "-- " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    Write-Host "   " -NoNewline
    Write-Host "前端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $FrontendPort) -NoNewline -ForegroundColor DarkGray
    if ($feUp) { Write-Host "ON " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    else { Write-Host "-- " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }

    if ($beProcs.Count -gt 1) {
        Write-Host ("    uvicorn x{0} !" -f $beProcs.Count) -ForegroundColor Yellow
    } elseif ($beProcs.Count -eq 1) {
        Write-Host ("    pid {0}" -f $beProcs[0].ProcessId) -ForegroundColor DarkGray
    } else {
        Write-Host "    no uvicorn" -ForegroundColor DarkGray
    }
}

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "  ========================================================" -ForegroundColor DarkCyan
    Write-Host "    " -NoNewline
    Write-Host "毕设港" -NoNewline -ForegroundColor Cyan
    Write-Host "  ·  Gate  ·  控制台" -ForegroundColor Gray
    Write-Host "  ========================================================" -ForegroundColor DarkCyan

    Show-StatusStrip

    Write-BlockTitle "服务"
    Write-Pair "1" "启动后端"      "2" "启动前端"
    Write-Pair "3" "前后端一起开"  "8" "重启后端" "Cyan" "Gray"
    Write-Pair "4" "停止后端"      "5" "停止前端"
    Write-Pair "6" "全部停止"      "7" "清理重复后端" "Gray" "Yellow"

    Write-BlockTitle "打开"
    Write-Pair "9" "运营台 UI"     "A" "API 文档"
    Write-Pair "B" "健康检查"      "C" "仓库目录"
    Write-Pair "D" "工作区"        "E" "上传目录"
    Write-Pair "S" "样例开题"

    Write-BlockTitle "Compose 库 / 其他"
    Write-Pair "F" "起 Compose 库"  "G" "Compose 状态"
    Write-Pair "H" "停 Compose 库"  "R" "刷新状态"
    Write-Pair "V" "检查 bat 编码"  "0" "退出" "Gray" "DarkGray"

    Write-Host ""
    Write-Host "  UI  $UiUrl" -ForegroundColor DarkGray
    Write-Host "  API $ApiUrl   docs $DocsUrl" -ForegroundColor DarkGray
    Write-Host ""
}

while ($true) {
    Show-Menu
    Write-Host "  请选择" -NoNewline -ForegroundColor Cyan
    $choice = (Read-Host " ").Trim().ToUpperInvariant()

    switch ($choice) {
        "1" {
            Start-InNewWindow "GF-Backend" (Join-Path $Scripts "start-backend.bat")
            Start-Sleep -Seconds 1
        }
        "2" {
            Start-InNewWindow "GF-Frontend" (Join-Path $Scripts "start-frontend.bat")
            Start-Sleep -Seconds 1
        }
        "3" {
            Start-InNewWindow "GF-Backend" (Join-Path $Scripts "start-backend.bat")
            Start-Sleep -Milliseconds 700
            Start-InNewWindow "GF-Frontend" (Join-Path $Scripts "start-frontend.bat")
            Start-Sleep -Seconds 1
        }
        "4" {
            Write-Line "  停止后端..." "Cyan"
            Stop-BackendAll
            Pause-Menu
        }
        "5" {
            Write-Line "  停止前端..." "Cyan"
            Stop-FrontendAll
            Pause-Menu
        }
        "6" {
            Write-Line "  全部停止..." "Cyan"
            Stop-FrontendAll
            Stop-BackendAll
            Pause-Menu
        }
        "7" {
            Write-Line "  清理重复后端..." "Cyan"
            Invoke-LocalBat (Join-Path $Scripts "kill-dup-backend.bat")
            Pause-Menu
        }
        "8" {
            Write-Line "  重启后端..." "Cyan"
            Stop-BackendAll
            Start-Sleep -Milliseconds 500
            Start-InNewWindow "GF-Backend" (Join-Path $Scripts "start-backend.bat")
            Start-Sleep -Seconds 1
        }
        "9" {
            Open-PathOrUrl $UiUrl
            Start-Sleep -Milliseconds 400
        }
        "A" {
            Open-PathOrUrl $DocsUrl
            Start-Sleep -Milliseconds 400
        }
        "B" {
            Write-Line "  GET $HealthUrl" "DarkGray"
            $h = Invoke-HealthCheck
            if ($h.ok) {
                Write-Line "  [OK] $($h.body)" "Green"
            } else {
                Write-Line "  [FAIL] $($h.body)" "Red"
            }
            Pause-Menu
        }
        "C" {
            Open-PathOrUrl $Repo
            Start-Sleep -Milliseconds 300
        }
        "D" {
            $p = Join-Path $Repo "data\workspace"
            if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
            Open-PathOrUrl $p
            Start-Sleep -Milliseconds 300
        }
        "E" {
            $p = Join-Path $Repo "data\uploads"
            if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
            Open-PathOrUrl $p
            Start-Sleep -Milliseconds 300
        }
        "S" {
            $p = Join-Path $Repo "data\samples"
            if (-not (Test-Path $p)) {
                Write-Line "  [提示] 尚无 data/samples" "Yellow"
                Pause-Menu
            } else {
                Open-PathOrUrl $p
                Start-Sleep -Milliseconds 300
            }
        }
        "F" {
            Invoke-Docker @("up", "-d")
            Pause-Menu
        }
        "G" {
            Invoke-Docker @("ps")
            Pause-Menu
        }
        "H" {
            Write-Line "  将停止 docker-compose 中的 MySQL 容器（非本机 MySQL80；数据卷默认保留）" "Yellow"
            Invoke-Docker @("down")
            Pause-Menu
        }
        "R" { continue }
        "V" {
            Invoke-LocalBat (Join-Path $Scripts "verify-bats.bat")
            Pause-Menu
        }
        "0" { exit 0 }
        "" { continue }
        default {
            Write-Line "  [提示] 无效选项：$choice" "Yellow"
            Start-Sleep -Milliseconds 700
        }
    }
}