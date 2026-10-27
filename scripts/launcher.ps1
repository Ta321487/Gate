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
$FrontendPort = 5300
$UiUrl = "http://127.0.0.1:$FrontendPort"
$ApiUrl = "http://127.0.0.1:$BackendPort"
$DocsUrl = "$ApiUrl/docs"
$HealthUrl = "$ApiUrl/api/health"
$ColWidth = 26
# 启后端前是否先清 :8000（可用 T 切换；环境变量 GF_NO_AUTO_KILL=1 默认关）
$script:AutoKillOnStart = -not (
    $env:GF_NO_AUTO_KILL -eq "1" -or $env:GF_NO_AUTO_KILL -eq "true"
)

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

function Show-PortOccupants([int]$Port, [string]$Label) {
    $rows = @(Get-GfPortOccupants -Port $Port -RepoRoot $Repo)
    if ($rows.Count -eq 0) {
        Write-Line ("  {0}（:{1}）空闲" -f $Label, $Port) "DarkGray"
        return $rows
    }
    Write-Line ("  {0}（:{1}）被 {2} 个程序占用：" -f $Label, $Port, $rows.Count) "Yellow"
    foreach ($r in $rows) {
        $tag = if ($r.Ours) { "当前服务" } else { "其他程序" }
        $color = if ($r.Ours) { "Green" } else { "Yellow" }
        Write-Line ("    #{0}  [{1}]  {2}" -f $r.Pid, $tag, $r.Name) $color
        if ($r.Cmd) {
            Write-Line ("           {0}" -f $r.Cmd) "DarkGray"
        }
    }
    return $rows
}

function Show-AllPortOccupants {
    Write-Line "  端口使用情况" "Cyan"
    [void](Show-PortOccupants $BackendPort "后端")
    [void](Show-PortOccupants $FrontendPort "前端")
    if ($script:AutoKillOnStart) {
        Write-Line ("  启动前自动释放：开 · 启动后端时会先腾出 :{0}" -f $BackendPort) "DarkGray"
    } else {
        Write-Line "  启动前自动释放：关 · 不会自动结束占用中的程序" "DarkGray"
    }
    Write-Line "  按 T 可切换；若希望默认关闭，启动前设置 GF_NO_AUTO_KILL=1" "DarkGray"
}

function Stop-PortOccupants([int]$Port, [string]$Label) {
    $rows = @(Get-GfPortOccupants -Port $Port -RepoRoot $Repo)
    if ($rows.Count -eq 0) {
        Write-Line ("  {0}（:{1}）无需释放" -f $Label, $Port) "DarkGray"
        return
    }
    [void](Show-PortOccupants $Port $Label)
    Write-Line ("  正在释放 {0}（:{1}）..." -f $Label, $Port) "Cyan"
    # Listen PID may be venv re-exec child; resolve to outermost python before kill.
    $targets = @(
        $rows | ForEach-Object { Get-GfPythonTreeRoot -ProcessId ([int]$_.Pid) }
    ) | Select-Object -Unique
    $roots = @(Get-GfTreeRootPids -ProcessIds $targets)
    foreach ($id in $roots) {
        $r = Stop-GfProcessTree -ProcessId $id
        if ($r.ok) {
            Write-Line ("  [完成] 已结束 #{0}" -f $id) "Green"
        } else {
            $hint = if ($r.message -match 'Access denied|venv') {
                "系统拒绝结束（venv 子进程常见）；可再按 K，或关掉对应后端窗口"
            } else {
                $r.message
            }
            Write-Line ("  [提示] 未能结束 #{0}：{1}" -f $id, $hint) "Yellow"
        }
    }
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
        Write-Line ("  [跳过] 后端已在运行（进程 #{0}）" -f (Read-GfBackendPid -RepoRoot $Repo)) "Green"
        return
    }

    if ($script:AutoKillOnStart) {
        Write-Line "  正在准备并启动后端..." "DarkGray"
        Stop-BackendAll
    } else {
        Write-Line "  启动前自动释放已关闭，将直接尝试启动" "Yellow"
        if (Test-PortListening $BackendPort) {
            Write-Line ("  [错误] 后端端口 :{0} 仍被占用" -f $BackendPort) "Red"
            [void](Show-PortOccupants $BackendPort "后端")
            Write-Line "  可按 K 释放端口，或按 T 打开「启动前自动释放」后再启动" "DarkGray"
            return
        }
    }
    if (-not (Wait-BackendPortFree 12)) {
        Write-Line ("  [错误] 后端端口 :{0} 仍被占用" -f $BackendPort) "Red"
        [void](Show-PortOccupants $BackendPort "后端")
        Write-Line "  可按 K 释放端口，或按 8 清理多余的后端进程" "DarkGray"
        return
    }

    # launcher 已清过；tab 内 skip 二次 kill
    Start-BackendTab -SkipClean
    Write-Line "  等待就绪..." "DarkGray"
    $ready = Wait-BackendReady 25
    if ($ready.ok) {
        Write-Line ("  [完成] 后端已就绪（进程 #{0}）· {1}" -f (Read-GfBackendPid -RepoRoot $Repo), $ready.body) "Green"
    } else {
        Write-Line "  [错误] 后端未就绪" "Red"
        if ($ready.health) {
            Write-Line ("  （已有响应，但不是本次启动的进程 #{0}）" -f (Read-GfBackendPid -RepoRoot $Repo)) "Yellow"
        } else {
            Write-Line "  （$($ready.body)）" "Yellow"
        }
        Write-Line "  请查看后端窗口日志，或按 2 重试" "DarkGray"
    }
}

function Start-FrontendService {
    if (Test-PortListening $FrontendPort) {
        $rows = @(Get-GfPortOccupants -Port $FrontendPort -RepoRoot $Repo)
        Write-Line ("  [跳过] 前端已在运行（:{0}）" -f $FrontendPort) "Green"
        foreach ($r in $rows) {
            Write-Line ("    #{0}  {1}" -f $r.Pid, $r.Name) "DarkGray"
            if ($r.Cmd) { Write-Line ("           {0}" -f $r.Cmd) "DarkGray" }
        }
        Write-Line "  若不是本控制台拉起的前端，可按 K 释放后再开" "DarkGray"
        return
    }
    Start-InNewWindow "GF-Frontend" (Join-Path $Scripts "start-frontend.bat")
    Write-Line "  等待前端..." "DarkGray"
    if (Wait-PortUp $FrontendPort 25) {
        Write-Line ("  [完成] 前端已就绪（:{0}）" -f $FrontendPort) "Green"
    } else {
        Write-Line "  [警告] 窗口已开，:$FrontendPort 尚未就绪" "Yellow"
        [void](Show-PortOccupants $FrontendPort "前端")
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
    if ($beHealth.ok) { Write-Host "运行中 " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    elseif ($bePort) { Write-Host "占用中 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    else { Write-Host "未启动 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    Write-Host "   " -NoNewline
    Write-Host "前端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $FrontendPort) -NoNewline -ForegroundColor DarkGray
    if ($feUp) { Write-Host "运行中 " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    else { Write-Host "未启动 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }

    if (-not $pyExists) {
        Write-Host "    未找到 Python 环境（backend\.venv）" -ForegroundColor Red
    } elseif ($beHealth.ok -and $oursAlive) {
        Write-Host ("    进程 #{0}" -f $oursPid) -ForegroundColor DarkGray
    } elseif ($beHealth.ok) {
        Write-Host "    已响应，但不是本次启动的进程 · 按 2 可接管" -ForegroundColor Yellow
    } elseif ($bePort) {
        Write-Host "    端口被占用，服务未正常响应" -ForegroundColor Yellow
        $foreign = @(Get-GfPortOccupants -Port $BackendPort -RepoRoot $Repo | Where-Object { -not $_.Ours })
        if ($foreign.Count -gt 0) {
            Write-Host (" · 其他程序 #{0}（P 查看 · K 释放）" -f (($foreign | ForEach-Object { $_.Pid }) -join ",")) -ForegroundColor Yellow
        }
    } else {
        Write-Host "" -ForegroundColor DarkGray
    }
    if (-not $script:AutoKillOnStart) {
        Write-Host "  启动前自动释放：关" -ForegroundColor Yellow
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
    Write-Pair "1" "前后端一起开"  "2" "重启后端" "Cyan" "Cyan"
    Write-Pair "3" "只开后端"      "4" "只开前端"
    Write-Pair "5" "全部停止"      "8" "清理多余后端" "Gray" "Yellow"

    Write-BlockTitle "停止 / 打开"
    Write-Pair "6" "停后端"        "7" "停前端"
    Write-Pair "9" "打开控制台"   "A" "接口文档"
    Write-Pair "B" "健康检查"      "C" "打开项目目录"
    Write-Pair "D" "打开工作区"    "E" "打开上传目录"
    Write-Pair "S" "样例开题"

    Write-BlockTitle "端口"
    Write-Pair "P" "查看占用"     "K" "释放端口" "Yellow" "Yellow"
    Write-Pair "T" "启动前自动释放 开/关" "" "" "Gray" "Gray"

    Write-BlockTitle "数据库 / 其他"
    Write-Pair "F" "启动 Compose 库"  "G" "Compose 状态"
    Write-Pair "H" "停止 Compose 库"  "R" "刷新"
    Write-Pair "V" "检查脚本编码"    "0" "退出" "Gray" "DarkGray"

    Write-Host ""
    Write-Host "  控制台  $UiUrl" -ForegroundColor DarkGray
    Write-Host "  接口    $ApiUrl   文档 $DocsUrl" -ForegroundColor DarkGray
    $autoHint = if ($script:AutoKillOnStart) { "启动前自动释放：开" } else { "启动前自动释放：关" }
    Write-Host ("  快捷    launcher.bat 1 | 2 | 5   · {0}" -f $autoHint) -ForegroundColor DarkGray
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
            Write-Line "  正在清理多余的后端进程..." "Cyan"
            Invoke-LocalPs1 (Join-Path $Scripts "kill-dup-backend.ps1")
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "P" {
            Show-AllPortOccupants
            if ($script:CliMode) { return "ok" }
            Pause-Menu "按 Enter 返回菜单..."
            return "ok"
        }
        "K" {
            Write-Line "  正在释放前后端端口..." "Cyan"
            Stop-PortOccupants $BackendPort "后端"
            Stop-PortOccupants $FrontendPort "前端"
            Show-StatusStrip
            Flash-ThenContinue 900
            return "ok"
        }
        "T" {
            $script:AutoKillOnStart = -not $script:AutoKillOnStart
            if ($script:AutoKillOnStart) {
                $env:GF_NO_AUTO_KILL = "0"
                Write-Line ("  启动前自动释放：已打开（下次启动后端会先腾出 :{0}）" -f $BackendPort) "Green"
            } else {
                $env:GF_NO_AUTO_KILL = "1"
                Write-Line "  启动前自动释放：已关闭（占用时请按 P 查看或 K 释放）" "Yellow"
            }
            Flash-ThenContinue 900
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
