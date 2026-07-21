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
. (Join-Path $Scripts "_backend-procs.ps1")
$BackendPort = $script:GfBackendPort
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
    # 优先 TcpClient：Get-NetTCPConnection 在部分环境会漏检已 Listen 的端口
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $waited = $async.AsyncWaitHandle.WaitOne(500, $false)
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

function Get-BackendProcInfo {
    return (Get-GfBackendProcs -Port $BackendPort)
}

function Get-BackendProcs {
    $r = Get-BackendProcInfo
    return @($r.Procs)
}

function Test-BackendPythonEnv([switch]$CheckImport) {
    return (Get-GfBackendPythonEnv -RepoRoot $Repo -CheckImport:$CheckImport)
}

function Test-BackendListenerIsRepoVenv {
    if (Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort) {
        return $true
    }
    $info = Get-BackendProcInfo
    $listenPids = @($info.ListenPids)
    if ($listenPids.Count -eq 0) { return $false }
    $listeners = @($info.Procs | Where-Object { $listenPids -contains $_.ProcessId })
    if ($listeners.Count -eq 0) { return $false }
    $ok = @($listeners | Where-Object { Test-GfProcUsesRepoVenv -Proc $_ -RepoRoot $Repo })
    return ($ok.Count -eq $listeners.Count -and $ok.Count -gt 0)
}

function Write-BackendVenvHints {
    $info = Get-BackendProcInfo
    $listenPids = @($info.ListenPids)
    $ours = Read-GfBackendPid -RepoRoot $Repo
    $protected = Get-GfProtectedBackendPids -ListenPids $listenPids
    $foreign = @($info.Procs | Where-Object { -not $protected.ContainsKey([int]$_.ProcessId) })
    if ($ours -and (Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort)) {
        if ($foreign.Count -gt 0) {
            Write-Line ("  [提示] 本仓库 venv 已在听（pid {0}）；另有 {1} 个无关进程，按 7 清理" -f $ours, $foreign.Count) "DarkGray"
        }
        return
    }
    if ($listenPids.Count -gt 0) {
        Write-Line ("  [警告] :{0} 监听 pid={1}，不是本次 venv 启动（请按 8）" -f $BackendPort, ($listenPids -join ",")) "Yellow"
    }
    if ($foreign.Count -gt 0) {
        Write-Line ("  [提示] 另有 {0} 个无关 uvicorn，按 7 可清理" -f $foreign.Count) "DarkGray"
    }
}

function Invoke-HealthCheck([int]$TimeoutSec = 2) {
    try {
        $r = Invoke-RestMethod -Uri $HealthUrl -TimeoutSec $TimeoutSec
        return @{ ok = $true; body = ($r | ConvertTo-Json -Compress) }
    } catch {
        return @{ ok = $false; body = $_.Exception.Message }
    }
}

function Wait-BackendReady([int]$TimeoutSec = 30) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $h = Invoke-HealthCheck -TimeoutSec 1
        $ours = Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort
        if ($h.ok -and $ours) {
            return @{ ok = $true; body = $h.body }
        }
        Start-Sleep -Milliseconds 400
    }
    $h2 = Invoke-HealthCheck -TimeoutSec 2
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
        Start-Sleep -Milliseconds 300
    }
    return -not (Test-PortListening $BackendPort)
}

function Start-BackendService([switch]$ForceRestart) {
    $envCheck = Test-BackendPythonEnv -CheckImport
    if (-not $envCheck.ok) {
        if (-not $envCheck.exists) {
            Write-Line "  [错误] 缺少 backend\.venv\Scripts\python.exe · 请先创建 venv 并安装依赖" "Red"
        } elseif ($envCheck.uvicorn -eq $false) {
            Write-Line "  [错误] venv 无法 import uvicorn · 请在 backend 执行 pip install -r requirements.txt" "Red"
        } else {
            Write-Line "  [错误] $($envCheck.message)" "Red"
        }
        return
    }
    Write-Line "  [环境] venv 文件可用（import uvicorn OK）" "DarkGray"

    $health = Invoke-HealthCheck
    $oursOk = Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort
    if ($health.ok -and $oursOk -and -not $ForceRestart) {
        Write-Line ("  [跳过] 本仓库 venv 已在运行 pid={0} · {1}" -f (Read-GfBackendPid -RepoRoot $Repo), $health.body) "Green"
        Write-BackendVenvHints
        return
    }

    Write-Line "  清理旧进程并启动本仓库 venv ..." "DarkGray"
    Stop-BackendAll
    if (-not (Wait-BackendPortFree 15)) {
        Write-Line "  [错误] :$BackendPort 仍被占用，无法启动" "Red"
        return
    }

    # 同窗 WT 标签启动（start-backend.ps1 写 pidfile；venv 父子进程由进程树识别）
    Start-InNewWindow "GF-Backend" (Join-Path $Scripts "start-backend.bat")
    Write-Line "  等待本仓库进程就绪（health + 端口归属）..." "DarkGray"
    $ready = Wait-BackendReady 35
    if ($ready.ok) {
        Write-Line ("  [OK] {0} · pid={1} 本仓库 venv" -f $ready.body, (Read-GfBackendPid -RepoRoot $Repo)) "Green"
        Write-BackendVenvHints
    } else {
        Write-Line "  [错误] 未能用本仓库 venv 接管 :$BackendPort" "Red"
        if ($ready.health) {
            Write-Line ("  （端口有响应，但不是本次启动的 pid={0}）" -f (Read-GfBackendPid -RepoRoot $Repo)) "Yellow"
        } else {
            Write-Line "  （健康检查失败：$($ready.body)）" "Yellow"
        }
        Write-Line "  请查看 GF-Backend 标签页日志，或按 8 重试" "DarkGray"
    }
}

function Test-WindowsTerminalCli {
    return [bool](Get-Command wt -ErrorAction SilentlyContinue)
}

function Start-InNewWindow([string]$Title, [string]$BatPath) {
    <# 兼容旧名：优先 Windows Terminal 同窗新标签；无 wt 则弹独立 cmd。
       单独双击 start-*.bat 仍是独立窗口，不受影响。 #>
    Start-ServiceHost -Title $Title -BatPath $BatPath
}

function Start-ServiceHost([string]$Title, [string]$BatPath) {
    if (-not (Test-Path -LiteralPath $BatPath)) {
        Write-Line "  [错误] 找不到 $BatPath" "Red"
        return
    }
    # GF_LAUNCH_STYLE=window 强制独立 cmd（调试用）
    $forceWindow = ($env:GF_LAUNCH_STYLE -eq "window")
    $inner = "title $Title & call `"$BatPath`""
    if (-not $forceWindow -and (Test-WindowsTerminalCli)) {
        # 固定挂到命名窗口（与 launcher.bat / $script:GfWtWindow 一致）
        $arg = @(
            "-w", $script:GfWtWindow,
            "nt",
            "--title", $Title,
            "-d", $Repo,
            "--",
            "cmd", "/k",
            $inner
        )
        try {
            Start-Process -FilePath "wt.exe" -ArgumentList $arg | Out-Null
            Write-Line ("  [完成] 已开标签页：$Title（窗口 {0}）" -f $script:GfWtWindow) "Green"
            return
        } catch {
            Write-Line "  [警告] wt 开标签失败，回退独立窗口" "Yellow"
        }
    }
    Start-Process -FilePath "cmd.exe" -WorkingDirectory $Repo -ArgumentList @(
        "/k",
        $inner
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
    # 后端：health 通了就一定是 ON（不再被「未运行」文案盖掉）
    $beHealth = Invoke-HealthCheck -TimeoutSec 2
    $bePort = Test-PortListening $BackendPort
    $feUp = Test-PortListening $FrontendPort
    $beProcs = @(Get-BackendProcs)
    $pyEnv = Test-BackendPythonEnv   # 状态条只查 venv 是否存在，不每次 import

    Write-Host ""
    Write-Host "  " -NoNewline
    Write-Host "后端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $BackendPort) -NoNewline -ForegroundColor DarkGray
    if ($beHealth.ok) { Write-Host "ON " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    elseif ($bePort) { Write-Host "端口开/health失败 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    else { Write-Host "-- " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    Write-Host "   " -NoNewline
    Write-Host "前端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $FrontendPort) -NoNewline -ForegroundColor DarkGray
    if ($feUp) { Write-Host "ON " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    else { Write-Host "-- " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }

    if (-not $pyEnv.exists) {
        Write-Host "    venv 缺失" -ForegroundColor Red
    } elseif ($beHealth.ok) {
        $oursPid = Read-GfBackendPid -RepoRoot $Repo
        $oursLive = Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort
        if ($oursLive) {
            Write-Host ("    health OK · venv pid {0}" -f $oursPid) -ForegroundColor DarkGray
        } elseif ($beProcs.Count -gt 1) {
            Write-Host ("    health OK · uvicorn×{0}（非本次venv，请按8）" -f $beProcs.Count) -ForegroundColor Yellow
        } elseif ($beProcs.Count -ge 1) {
            Write-Host ("    health OK · 非本次venv · pid {0}（请按8）" -f $beProcs[-1].ProcessId) -ForegroundColor Yellow
        } else {
            Write-Host "    health OK" -ForegroundColor DarkGray
        }
    } elseif ($bePort) {
        Write-Host "    端口可连但 /api/health 失败" -ForegroundColor Yellow
    } elseif ($beProcs.Count -gt 1) {
        Write-Host ("    uvicorn×{0} 僵死未就绪（请按 7 或 8）" -f $beProcs.Count) -ForegroundColor Yellow
    } elseif ($beProcs.Count -eq 1) {
        Write-Host ("    pid {0} 未监听（请按 7 或 8）" -f $beProcs[0].ProcessId) -ForegroundColor Yellow
    } else {
        Write-Host "    未运行 · venv OK" -ForegroundColor DarkGray
    }
}

function Show-StatusAfterAction {
    Write-Host ""
    Write-Host "  -------- 操作后状态（上面菜单是启动前的快照）--------" -ForegroundColor DarkCyan
    Show-StatusStrip
}

function Wait-PortUp([int]$Port, [int]$TimeoutSec = 25) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $Port) { return $true }
        Start-Sleep -Milliseconds 400
    }
    return (Test-PortListening $Port)
}

function Start-FrontendService {
    if (Test-PortListening $FrontendPort) {
        Write-Line "  [跳过] 前端已在监听 :$FrontendPort" "Green"
        return
    }
    Start-InNewWindow "GF-Frontend" (Join-Path $Scripts "start-frontend.bat")
    Write-Line "  等待前端 :$FrontendPort ..." "DarkGray"
    if (Wait-PortUp $FrontendPort 30) {
        Write-Line "  [OK] 前端已监听 :$FrontendPort" "Green"
    } else {
        Write-Line "  [警告] 前端窗口已开，但 :$FrontendPort 尚未就绪" "Yellow"
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
    if (Test-WindowsTerminalCli) {
        Write-Host ("  服务启动 → Windows Terminal 窗口 {0} 的标签页（单独 bat 仍可独立窗口）" -f $script:GfWtWindow) -ForegroundColor DarkGray
    }
    Write-Host ""
}

while ($true) {
    Show-Menu
    Write-Host "  请选择" -NoNewline -ForegroundColor Cyan
    $choice = (Read-Host " ").Trim().ToUpperInvariant()

    switch ($choice) {
        "1" {
            Start-BackendService
            Show-StatusAfterAction
            Pause-Menu
        }
        "2" {
            Start-FrontendService
            Show-StatusAfterAction
            Pause-Menu
        }
        "3" {
            Start-BackendService
            Start-FrontendService
            Show-StatusAfterAction
            Pause-Menu
        }
        "4" {
            Write-Line "  停止后端..." "Cyan"
            Stop-BackendAll
            Show-StatusAfterAction
            Pause-Menu
        }
        "5" {
            Write-Line "  停止前端..." "Cyan"
            Stop-FrontendAll
            Show-StatusAfterAction
            Pause-Menu
        }
        "6" {
            Write-Line "  全部停止..." "Cyan"
            Stop-FrontendAll
            Stop-BackendAll
            Show-StatusAfterAction
            Pause-Menu
        }
        "7" {
            Write-Line "  清理重复后端..." "Cyan"
            Invoke-LocalBat (Join-Path $Scripts "kill-dup-backend.bat")
            Show-StatusAfterAction
            Pause-Menu
        }
        "8" {
            Write-Line "  重启后端..." "Cyan"
            Start-BackendService -ForceRestart
            Show-StatusAfterAction
            Pause-Menu
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