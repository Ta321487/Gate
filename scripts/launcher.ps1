# Gate console launcher
# Entry: scripts\launcher.bat [action]
# Save as UTF-8 with BOM (Chinese + Windows PowerShell 5.1)
#
# Hot keys (daily): 1 both | 2 restart BE | 5 stop all | 0 quit
# CLI:  scripts\launcher.bat 1
#       scripts\launcher.bat restart

param(
    [Parameter(Position = 0)]
    [string]$Go = ""
)

$ErrorActionPreference = "Continue"
$script:CliMode = -not [string]::IsNullOrWhiteSpace($Go)

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
. (Join-Path $Scripts "_backend-procs.ps1")
$BackendPort = $script:GfBackendPort
$FrontendPort = 5173
$UiUrl = "http://127.0.0.1:$FrontendPort"
$ApiUrl = "http://127.0.0.1:$BackendPort"
$DocsUrl = "$ApiUrl/docs"
$HealthUrl = "$ApiUrl/api/health"
$ColWidth = 26

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

function Pause-Menu([string]$Hint = "按 Enter 继续...") {
    if ($script:CliMode) { return }
    Write-Host ""
    Write-Host "  $Hint" -ForegroundColor DarkGray
    [void][Console]::ReadLine()
}

function Flash-ThenContinue([int]$Ms = 700) {
    # Hot-path: show result briefly, then redraw menu (no Enter)
    if ($script:CliMode) { return }
    Start-Sleep -Milliseconds $Ms
}

function Test-PortListening([int]$Port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $waited = $async.AsyncWaitHandle.WaitOne(280, $false)
        if ($waited -and $client.Connected) {
            try { $client.EndConnect($async) } catch {}
            $client.Close()
            return $true
        }
        try { $client.Close() } catch {}
    } catch {}
    try {
        $rows = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        return ($rows.Count -gt 0)
    } catch {
        return $false
    }
}

function Test-BackendPythonEnv([switch]$CheckImport) {
    return (Get-GfBackendPythonEnv -RepoRoot $Repo -CheckImport:$CheckImport)
}

function Invoke-HealthCheck([int]$TimeoutSec = 1) {
    try {
        $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec $TimeoutSec
        return @{ ok = $true; body = ($r | ConvertTo-Json -Compress) }
    } catch {
        return @{ ok = $false; body = $_.Exception.Message }
    }
}

function Wait-BackendReady([int]$TimeoutSec = 25) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $h = Invoke-HealthCheck -TimeoutSec 1
        $ours = Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort
        if ($h.ok -and $ours) {
            return @{ ok = $true; body = $h.body }
        }
        Start-Sleep -Milliseconds 350
    }
    $h2 = Invoke-HealthCheck -TimeoutSec 1
    return @{
        ok     = $false
        body   = $h2.body
        health = $h2.ok
    }
}

function Wait-BackendPortFree([int]$TimeoutSec = 10) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-PortListening $BackendPort)) { return $true }
        Start-Sleep -Milliseconds 250
    }
    return -not (Test-PortListening $BackendPort)
}

function Wait-PortUp([int]$Port, [int]$TimeoutSec = 25) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $Port) { return $true }
        Start-Sleep -Milliseconds 350
    }
    return (Test-PortListening $Port)
}

function Test-WindowsTerminalCli {
    return [bool](Get-Command wt -ErrorAction SilentlyContinue)
}

function Start-ServiceHostCmd([string]$Title, [string]$InnerCmd) {
    $forceWindow = ($env:GF_LAUNCH_STYLE -eq "window")
    if (-not $forceWindow -and (Test-WindowsTerminalCli)) {
        $arg = @(
            "-w", $script:GfWtWindow,
            "nt",
            "--title", $Title,
            "-d", $Repo,
            "--",
            "cmd", "/k",
            $InnerCmd
        )
        try {
            Start-Process -FilePath "wt.exe" -ArgumentList $arg | Out-Null
            Write-Line ("  [完成] 标签页 $Title") "Green"
            return
        } catch {
            Write-Line "  [警告] wt 开标签失败，回退独立窗口" "Yellow"
        }
    }
    Start-Process -FilePath "cmd.exe" -WorkingDirectory $Repo -ArgumentList @(
        "/k",
        $InnerCmd
    ) | Out-Null
    Write-Line "  [完成] 窗口 $Title" "Green"
}

function Start-InNewWindow([string]$Title, [string]$BatPath) {
    if (-not (Test-Path -LiteralPath $BatPath)) {
        Write-Line "  [错误] 找不到 $BatPath" "Red"
        return
    }
    Start-ServiceHostCmd $Title ("title $Title & call `"$BatPath`"")
}

function Start-BackendTab([switch]$SkipClean) {
    $ps1 = Join-Path $Scripts "start-backend.ps1"
    if (-not (Test-Path -LiteralPath $ps1)) {
        Write-Line "  [错误] 找不到 $ps1" "Red"
        return
    }
    $flag = if ($SkipClean) { " -SkipClean" } else { "" }
    $inner = "title GF-Backend & powershell -NoProfile -ExecutionPolicy Bypass -File `"$ps1`"$flag"
    Start-ServiceHostCmd "GF-Backend" $inner
}

function Invoke-LocalBat([string]$BatPath, [string[]]$BatArgs = @()) {
    if (-not (Test-Path -LiteralPath $BatPath)) {
        Write-Line "  [错误] 找不到 $BatPath" "Red"
        return
    }
    & cmd.exe /c "call `"$BatPath`" $($BatArgs -join ' ')"
}

function Invoke-LocalPs1([string]$Ps1Path, [string[]]$Ps1Args = @()) {
    if (-not (Test-Path -LiteralPath $Ps1Path)) {
        Write-Line "  [错误] 找不到 $Ps1Path" "Red"
        return
    }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Ps1Path @Ps1Args
}

function Stop-BackendAll {
    Invoke-LocalPs1 (Join-Path $Scripts "kill-dup-backend.ps1") @("-All")
}

function Stop-FrontendAll {
    Invoke-LocalPs1 (Join-Path $Scripts "stop-frontend.ps1")
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
        Write-Line "  [错误] 未找到 docker（需要 Docker Desktop）" "Red"
        Write-Line "  说明：管的是 docker-compose 里的 MySQL 容器，不是本机 MySQL80" "DarkGray"
        return
    }
    Push-Location $Repo
    try {
        Write-Line ("  > docker compose {0}" -f ($ComposeArgs -join " ")) "DarkGray"
        & docker compose @ComposeArgs
        if ($LASTEXITCODE -ne 0) {
            Write-Line "  [警告] docker 退出码 $LASTEXITCODE" "Yellow"
        }
    } catch {
        Write-Line "  [错误] $($_.Exception.Message)" "Red"
    } finally {
        Pop-Location
    }
}

function Start-BackendService([switch]$ForceRestart) {
    $envCheck = Test-BackendPythonEnv -CheckImport
    if (-not $envCheck.ok) {
        if (-not $envCheck.exists) {
            Write-Line "  [错误] 缺少 backend\.venv · 先建 venv 并 pip install" "Red"
        } elseif ($envCheck.uvicorn -eq $false) {
            Write-Line "  [错误] venv 无法 import uvicorn · pip install -r requirements.txt" "Red"
        } else {
            Write-Line "  [错误] $($envCheck.message)" "Red"
        }
        return
    }

    $health = Invoke-HealthCheck
    $oursOk = Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort
    if ($health.ok -and $oursOk -and -not $ForceRestart) {
        Write-Line ("  [跳过] 后端已在跑 pid={0}" -f (Read-GfBackendPid -RepoRoot $Repo)) "Green"
        return
    }

    Write-Line "  清理并启动后端..." "DarkGray"
    Stop-BackendAll
    if (-not (Wait-BackendPortFree 12)) {
        Write-Line "  [错误] :$BackendPort 仍被占用" "Red"
        return
    }

    # launcher 已清过；tab 内 skip 二次 kill
    Start-BackendTab -SkipClean
    Write-Line "  等待就绪..." "DarkGray"
    $ready = Wait-BackendReady 25
    if ($ready.ok) {
        Write-Line ("  [OK] pid={0} · {1}" -f (Read-GfBackendPid -RepoRoot $Repo), $ready.body) "Green"
    } else {
        Write-Line "  [错误] 后端未就绪" "Red"
        if ($ready.health) {
            Write-Line ("  （有响应但非本仓库 pid={0}）" -f (Read-GfBackendPid -RepoRoot $Repo)) "Yellow"
        } else {
            Write-Line "  （$($ready.body)）" "Yellow"
        }
        Write-Line "  看 GF-Backend 标签页，或按 2 重试" "DarkGray"
    }
}

function Start-FrontendService {
    if (Test-PortListening $FrontendPort) {
        Write-Line "  [跳过] 前端已在 :$FrontendPort" "Green"
        return
    }
    Start-InNewWindow "GF-Frontend" (Join-Path $Scripts "start-frontend.bat")
    Write-Line "  等待前端..." "DarkGray"
    if (Wait-PortUp $FrontendPort 25) {
        Write-Line "  [OK] 前端 :$FrontendPort" "Green"
    } else {
        Write-Line "  [警告] 窗口已开，:$FrontendPort 尚未就绪" "Yellow"
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
    # Light strip: port + health + pidfile; skip heavy WMI unless needed
    $beHealth = Invoke-HealthCheck -TimeoutSec 1
    $bePort = Test-PortListening $BackendPort
    $feUp = Test-PortListening $FrontendPort
    $pyExists = Test-Path -LiteralPath (Get-GfBackendVenvPython -RepoRoot $Repo)
    $oursPid = Read-GfBackendPid -RepoRoot $Repo
    $oursAlive = $false
    if ($oursPid) {
        $oursAlive = [bool](Get-Process -Id $oursPid -ErrorAction SilentlyContinue)
    }

    Write-Host ""
    Write-Host "  " -NoNewline
    Write-Host "后端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $BackendPort) -NoNewline -ForegroundColor DarkGray
    if ($beHealth.ok) { Write-Host "ON " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    elseif ($bePort) { Write-Host "端口开 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    else { Write-Host "-- " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    Write-Host "   " -NoNewline
    Write-Host "前端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $FrontendPort) -NoNewline -ForegroundColor DarkGray
    if ($feUp) { Write-Host "ON " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    else { Write-Host "-- " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }

    if (-not $pyExists) {
        Write-Host "    venv 缺失" -ForegroundColor Red
    } elseif ($beHealth.ok -and $oursAlive) {
        Write-Host ("    pid {0}" -f $oursPid) -ForegroundColor DarkGray
    } elseif ($beHealth.ok) {
        Write-Host "    health OK（非本次 pid，按 2 接管）" -ForegroundColor Yellow
    } elseif ($bePort) {
        Write-Host "    端口开但 health 失败" -ForegroundColor Yellow
    } else {
        Write-Host "    未运行" -ForegroundColor DarkGray
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

    Write-BlockTitle "服务（高频）"
    Write-Pair "1" "前后端一起开"  "2" "重启后端" "Cyan" "Cyan"
    Write-Pair "3" "只开后端"      "4" "只开前端"
    Write-Pair "5" "全部停止"      "8" "清重复后端" "Gray" "Yellow"

    Write-BlockTitle "停止 / 打开"
    Write-Pair "6" "停后端"        "7" "停前端"
    Write-Pair "9" "运营台 UI"     "A" "API 文档"
    Write-Pair "B" "健康检查"      "C" "仓库目录"
    Write-Pair "D" "工作区"        "E" "上传目录"
    Write-Pair "S" "样例开题"

    Write-BlockTitle "Compose / 其他"
    Write-Pair "F" "起 Compose 库"  "G" "Compose 状态"
    Write-Pair "H" "停 Compose 库"  "R" "刷新"
    Write-Pair "V" "检查 bat 编码"  "0" "退出" "Gray" "DarkGray"

    Write-Host ""
    Write-Host "  UI  $UiUrl" -ForegroundColor DarkGray
    Write-Host "  API $ApiUrl   docs $DocsUrl" -ForegroundColor DarkGray
    Write-Host "  直达  launcher.bat 1 | 2 | 5   （启停后自动回菜单，不必按 Enter）" -ForegroundColor DarkGray
    Write-Host ""
}

function Resolve-Choice([string]$Raw) {
    $c = $Raw.Trim().ToUpperInvariant()
    switch ($c) {
        "BOTH" { return "1" }
        "ALL" { return "1" }
        "RESTART" { return "2" }
        "BE" { return "3" }
        "BACKEND" { return "3" }
        "FE" { return "4" }
        "FRONTEND" { return "4" }
        "STOP" { return "5" }
        "STOPALL" { return "5" }
        "QUIT" { return "0" }
        "EXIT" { return "0" }
        "Q" { return "0" }
        default { return $c }
    }
}

function Invoke-Choice([string]$Choice) {
    $c = Resolve-Choice $Choice
    switch ($c) {
        "1" {
            Start-BackendService
            Start-FrontendService
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "2" {
            Write-Line "  重启后端..." "Cyan"
            Start-BackendService -ForceRestart
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "3" {
            Start-BackendService
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "4" {
            Start-FrontendService
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "5" {
            Write-Line "  全部停止..." "Cyan"
            Stop-FrontendAll
            Stop-BackendAll
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "6" {
            Write-Line "  停止后端..." "Cyan"
            Stop-BackendAll
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "7" {
            Write-Line "  停止前端..." "Cyan"
            Stop-FrontendAll
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "8" {
            Write-Line "  清理重复后端..." "Cyan"
            Invoke-LocalPs1 (Join-Path $Scripts "kill-dup-backend.ps1")
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "9" {
            Open-PathOrUrl $UiUrl
            Flash-ThenContinue 400
            return "ok"
        }
        "A" {
            Open-PathOrUrl $DocsUrl
            Flash-ThenContinue 400
            return "ok"
        }
        "B" {
            Write-Line "  GET $HealthUrl" "DarkGray"
            $h = Invoke-HealthCheck
            if ($h.ok) { Write-Line "  [OK] $($h.body)" "Green" }
            else { Write-Line "  [FAIL] $($h.body)" "Red" }
            Pause-Menu
            return "ok"
        }
        "C" {
            Open-PathOrUrl $Repo
            Flash-ThenContinue 300
            return "ok"
        }
        "D" {
            $p = Join-Path $Repo "data\workspace"
            if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
            Open-PathOrUrl $p
            Flash-ThenContinue 300
            return "ok"
        }
        "E" {
            $p = Join-Path $Repo "data\uploads"
            if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
            Open-PathOrUrl $p
            Flash-ThenContinue 300
            return "ok"
        }
        "S" {
            $p = Join-Path $Repo "data\samples"
            if (-not (Test-Path $p)) {
                Write-Line "  [提示] 尚无 data/samples" "Yellow"
                Flash-ThenContinue 600
            } else {
                Open-PathOrUrl $p
                Flash-ThenContinue 300
            }
            return "ok"
        }
        "F" {
            Invoke-Docker @("up", "-d")
            Pause-Menu
            return "ok"
        }
        "G" {
            Invoke-Docker @("ps")
            Pause-Menu
            return "ok"
        }
        "H" {
            Write-Line "  停 Compose MySQL 容器（非本机 MySQL80；卷默认保留）" "Yellow"
            Invoke-Docker @("down")
            Pause-Menu
            return "ok"
        }
        "R" { return "ok" }
        "V" {
            Invoke-LocalBat (Join-Path $Scripts "verify-bats.bat")
            Pause-Menu
            return "ok"
        }
        "0" { return "exit" }
        "" { return "ok" }
        default {
            Write-Line "  [提示] 无效：$Choice  （1 一起开 · 2 重启 · 5 全停 · 0 退出）" "Yellow"
            if ($script:CliMode) { return "bad" }
            Start-Sleep -Milliseconds 800
            return "ok"
        }
    }
}

# --- entry -------------------------------------------------------------------

if ($script:CliMode) {
    $code = Invoke-Choice $Go
    if ($code -eq "exit") { exit 0 }
    if ($code -eq "bad") { exit 1 }
    exit 0
}

while ($true) {
    Show-Menu
    Write-Host "  请选择" -NoNewline -ForegroundColor Cyan
    $choice = (Read-Host " ")
    $result = Invoke-Choice $choice
    if ($result -eq "exit") { exit 0 }
}
