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
    $Host.UI.RawUI.WindowTitle = "毕设港 · 本地控制台"
} catch {}

function Ensure-ConsoleWinApi {
    if ($script:GfConsoleWinApiReady) { return $true }
    try {
        Add-Type -TypeDefinition @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class GfConsoleWin {
  public const int GWL_STYLE = -16;
  public const int WS_MAXIMIZEBOX = 0x00010000;
  public const int WS_THICKFRAME = 0x00040000;
  public const int SWP_NOMOVE = 0x0002;
  public const int SWP_NOSIZE = 0x0001;
  public const int SWP_NOZORDER = 0x0004;
  public const int SWP_FRAMECHANGED = 0x0020;
  [DllImport("kernel32.dll")] public static extern IntPtr GetConsoleWindow();
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
  [DllImport("user32.dll", CharSet = CharSet.Unicode)]
  public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr hWnd, int nIndex);
  [DllImport("user32.dll")] public static extern int SetWindowLong(IntPtr hWnd, int nIndex, int dwNewLong);
  [DllImport("user32.dll")] public static extern bool SetWindowPos(
    IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  public const int SW_RESTORE = 9;
  public static bool TitleLooksLikeGate(IntPtr h) {
    if (h == IntPtr.Zero) return false;
    var sb = new StringBuilder(512);
    GetWindowText(h, sb, sb.Capacity);
    string t = sb.ToString();
    return t.IndexOf("毕设港") >= 0 || t.IndexOf("Gate Console") >= 0 || t.IndexOf("本地控制台") >= 0;
  }
  public static IntPtr ResolveGateWindow() {
    IntPtr h = GetConsoleWindow();
    if (h != IntPtr.Zero) return h;
    h = FindWindow(null, "毕设港 · 本地控制台");
    if (h != IntPtr.Zero) return h;
    h = FindWindow(null, "Gate Console");
    if (h != IntPtr.Zero) return h;
    h = GetForegroundWindow();
    if (TitleLooksLikeGate(h)) return h;
    return IntPtr.Zero;
  }
  public static void LockRemoteChrome() {
    IntPtr h = ResolveGateWindow();
    if (h == IntPtr.Zero) return;
    ShowWindow(h, SW_RESTORE);
    int style = GetWindowLong(h, GWL_STYLE);
    style &= ~WS_MAXIMIZEBOX;
    style &= ~WS_THICKFRAME;
    SetWindowLong(h, GWL_STYLE, style);
    SetWindowPos(h, IntPtr.Zero, 0, 0, 0, 0,
      SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED);
  }
}
"@ -ErrorAction Stop
        $script:GfConsoleWinApiReady = $true
        return $true
    } catch {
        # 类型已加载过
        if ($_.Exception.Message -match "already exists") {
            $script:GfConsoleWinApiReady = $true
            return $true
        }
        return $false
    }
}

function Lock-ConsoleRemoteChrome {
    # 去掉最大化与拖拽改尺寸，保持遥控器固定窗
    if (-not (Ensure-ConsoleWinApi)) { return }
    try { [GfConsoleWin]::LockRemoteChrome() } catch {}
}

function Set-ConsoleRemoteSize {
    # 遥控器：窗高 = 缓冲高，避免竖向滚动条；高度刚好装下菜单
    param([int]$Cols = 52, [int]$Rows = 36)
    try {
        $ui = $Host.UI.RawUI
        $curWin = $ui.WindowSize
        # 先把窗口收到目标以内，才能把 Buffer 也收到同样大小（否则会报错留下滚动条）
        $stepW = [Math]::Min([int]$curWin.Width, $Cols)
        $stepH = [Math]::Min([int]$curWin.Height, $Rows)
        if ($stepW -lt 1) { $stepW = $Cols }
        if ($stepH -lt 1) { $stepH = $Rows }
        $ui.WindowSize = New-Object System.Management.Automation.Host.Size($stepW, $stepH)
        $ui.BufferSize = New-Object System.Management.Automation.Host.Size($Cols, $Rows)
        $ui.WindowSize = New-Object System.Management.Automation.Host.Size($Cols, $Rows)
    } catch {}
    try {
        cmd /c "mode con cols=$Cols lines=$Rows" | Out-Null
    } catch {}
    Lock-ConsoleRemoteChrome
}

$Scripts = $PSScriptRoot
$Repo = (Resolve-Path (Join-Path $Scripts "..")).Path
. (Join-Path $Scripts "_backend-procs.ps1")
$BackendPort = $script:GfBackendPort
$FrontendPort = 5300
$UiUrl = "http://127.0.0.1:$FrontendPort"
$ApiUrl = "http://127.0.0.1:$BackendPort"
$DocsUrl = "$ApiUrl/docs"
$HealthUrl = "$ApiUrl/api/health"
$ColWidth = 22
# 交互菜单默认缩成遥控器窗；CLI 直达（带参数）不改窗口
if (-not $script:CliMode) {
    Set-ConsoleRemoteSize
}
# 启后端前是否先清 :8000（可用 T 切换；环境变量 GF_NO_AUTO_KILL=1 默认关）
$script:AutoKillOnStart = -not (
    $env:GF_NO_AUTO_KILL -eq "1" -or $env:GF_NO_AUTO_KILL -eq "true"
)
# 后端 uvicorn 热重载（可用 U 切换；环境变量 GF_BACKEND_RELOAD=0 默认关）
$script:BackendReload = -not (
    $env:GF_BACKEND_RELOAD -eq "0" -or $env:GF_BACKEND_RELOAD -eq "false"
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
    Write-Line "  端口占用" "Cyan"
    [void](Show-PortOccupants $BackendPort "服务端")
    [void](Show-PortOccupants $FrontendPort "运营台")
    if ($script:AutoKillOnStart) {
        Write-Line ("  启动前清理端口：开 · 启动服务端时会先释放 :{0}" -f $BackendPort) "DarkGray"
    } else {
        Write-Line "  启动前清理端口：关 · 端口被占用时不会自动结束相关进程" "DarkGray"
    }
    Write-Line "  按 T 可切换" "DarkGray"
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
    $flags = @()
    if ($SkipClean) { $flags += "-SkipClean" }
    if (-not $script:BackendReload) { $flags += "-NoReload" }
    $flag = if ($flags.Count -gt 0) { " " + ($flags -join " ") } else { "" }
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
        Write-Line "  [错误] 未找到 Docker Desktop" "Red"
        Write-Line "  说明：仅管理本产品附带的本地演示库，不影响本机已安装的 MySQL" "DarkGray"
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
            Write-Line "  [错误] 运行环境未就绪 · 请按 N 查看环境自检" "Red"
        } elseif ($envCheck.uvicorn -eq $false) {
            Write-Line "  [错误] 运行环境不完整 · 请按 N 查看环境自检" "Red"
        } else {
            Write-Line "  [错误] $($envCheck.message)" "Red"
        }
        return
    }

    $health = Invoke-HealthCheck
    $oursOk = Test-GfOurBackendListening -RepoRoot $Repo -Port $BackendPort
    if ($health.ok -and $oursOk -and -not $ForceRestart) {
        Write-Line "  [跳过] 服务端已在运行" "Green"
        return
    }

    if ($script:AutoKillOnStart) {
        Write-Line "  正在启动服务端..." "DarkGray"
        Stop-BackendAll
    } else {
        Write-Line "  「启动前清理端口」已关闭，将直接尝试启动" "Yellow"
        if (Test-PortListening $BackendPort) {
            Write-Line ("  [错误] 服务端口 :{0} 仍被占用" -f $BackendPort) "Red"
            [void](Show-PortOccupants $BackendPort "服务端")
            Write-Line "  可按 K 释放端口，或按 T 开启「启动前清理端口」后再启动" "DarkGray"
            return
        }
    }
    if (-not (Wait-BackendPortFree 12)) {
        Write-Line ("  [错误] 服务端口 :{0} 仍被占用" -f $BackendPort) "Red"
        [void](Show-PortOccupants $BackendPort "服务端")
        Write-Line "  可按 K 释放端口，或按 8 清理重复实例" "DarkGray"
        return
    }

    # launcher 已清过；tab 内 skip 二次 kill
    if ($script:BackendReload) {
        Write-Line "  服务热重载：开" "DarkGray"
    } else {
        Write-Line "  服务热重载：关" "DarkGray"
    }
    Start-BackendTab -SkipClean
    Write-Line "  等待就绪..." "DarkGray"
    $ready = Wait-BackendReady 25
    if ($ready.ok) {
        Write-Line "  [完成] 服务端已就绪" "Green"
    } else {
        Write-Line "  [错误] 服务端未就绪" "Red"
        if ($ready.health) {
            Write-Line "  （端口已有响应，但并非本控制台拉起 · 按 2 可接管）" "Yellow"
        } else {
            Write-Line "  （$($ready.body)）" "Yellow"
        }
        Write-Line "  请查看服务端窗口日志，或按 2 重试" "DarkGray"
    }
}

function Start-FrontendService {
    if (Test-PortListening $FrontendPort) {
        $rows = @(Get-GfPortOccupants -Port $FrontendPort -RepoRoot $Repo)
        Write-Line ("  [跳过] 运营台已在运行（:{0}）" -f $FrontendPort) "Green"
        foreach ($r in $rows) {
            Write-Line ("    #{0}  {1}" -f $r.Pid, $r.Name) "DarkGray"
            if ($r.Cmd) { Write-Line ("           {0}" -f $r.Cmd) "DarkGray" }
        }
        Write-Line "  若不是本控制台拉起，可按 K 释放端口后再启动" "DarkGray"
        return
    }
    Start-InNewWindow "GF-Frontend" (Join-Path $Scripts "start-frontend.bat")
    Write-Line "  等待运营台就绪..." "DarkGray"
    if (Wait-PortUp $FrontendPort 25) {
        Write-Line ("  [完成] 运营台已就绪（:{0}）" -f $FrontendPort) "Green"
    } else {
        Write-Line "  [警告] 窗口已打开，运营台尚未就绪" "Yellow"
        [void](Show-PortOccupants $FrontendPort "运营台")
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
    Write-Host "  $Title" -ForegroundColor Cyan
}

function Test-CmdAvailable([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Show-EnvDoctor {
    # 环境自检：缺什么用人话说，不甩堆栈
    Write-BlockTitle "环境自检"
    $rows = @()
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) { $rows += @{ ok = $true; text = "Python 已就绪" } }
    else { $rows += @{ ok = $false; text = "缺少 Python 3.11+ · 安装后请重新打开本控制台" } }

    $venvPy = Get-GfBackendVenvPython -RepoRoot $Repo
    if (Test-Path -LiteralPath $venvPy) {
        $rows += @{ ok = $true; text = "服务端运行环境已就绪" }
    } else {
        $rows += @{ ok = $false; text = "服务端运行环境未就绪 · 请按文档完成 backend\\.venv 安装" }
    }

    if (Test-CmdAvailable "node") { $rows += @{ ok = $true; text = "Node.js 已就绪" } }
    else { $rows += @{ ok = $false; text = "缺少 Node.js 18+ · 安装后再启动运营台" } }

    if (Test-CmdAvailable "npm") { $rows += @{ ok = $true; text = "npm 已就绪" } }
    else { $rows += @{ ok = $false; text = "缺少 npm（通常随 Node.js 安装）" } }

    $feMods = Join-Path $Repo "frontend\node_modules"
    if (Test-Path -LiteralPath $feMods) {
        $rows += @{ ok = $true; text = "运营台依赖已安装" }
    } else {
        $rows += @{ ok = $false; text = "运营台依赖未安装 · 请在 frontend 目录执行 npm install" }
    }

    if (Test-CmdAvailable "java") { $rows += @{ ok = $true; text = "JDK 已就绪（预览学生包需要 17）" } }
    else { $rows += @{ ok = $false; text = "未检测到 JDK · 预览学生包需要 JDK 17" } }

    if (Test-CmdAvailable "mvn") { $rows += @{ ok = $true; text = "Maven 已就绪" } }
    else { $rows += @{ ok = $false; text = "未检测到 Maven · 构建学生包时需要" } }

    $envFile = Join-Path $Repo "backend\.env"
    $envExample = Join-Path $Repo "backend\.env.example"
    if (Test-Path -LiteralPath $envFile) {
        $rows += @{ ok = $true; text = "本机配置文件已就绪" }
    } elseif (Test-Path -LiteralPath $envExample) {
        $rows += @{ ok = $false; text = "缺少本机配置 · 可将 .env.example 复制为 .env 后按本机修改" }
    } else {
        $rows += @{ ok = $true; text = "可使用默认本机库（无需强制配置 .env）" }
    }

    foreach ($r in $rows) {
        if ($r.ok) { Write-Line ("  [通过] {0}" -f $r.text) "Green" }
        else { Write-Line ("  [待办] {0}" -f $r.text) "Yellow" }
    }
    Write-Line "  全部通过后，按 1 启动全部服务，再按 9 打开运营台" "DarkGray"
    $missing = @($rows | Where-Object { -not $_.ok }).Count
    return $missing
}

function Get-ServiceStatusSnapshot {
    # 探活可能要几百毫秒～1s；菜单应先出加载态再整页绘制
    $beHealth = Invoke-HealthCheck -TimeoutSec 1
    $bePort = Test-PortListening $BackendPort
    $feUp = Test-PortListening $FrontendPort
    $pyExists = Test-Path -LiteralPath (Get-GfBackendVenvPython -RepoRoot $Repo)
    $oursPid = Read-GfBackendPid -RepoRoot $Repo
    $oursAlive = $false
    if ($oursPid) {
        $oursAlive = [bool](Get-Process -Id $oursPid -ErrorAction SilentlyContinue)
    }
    $foreignCount = 0
    if ($bePort -and -not $beHealth.ok) {
        $foreignCount = @(
            Get-GfPortOccupants -Port $BackendPort -RepoRoot $Repo | Where-Object { -not $_.Ours }
        ).Count
    }
    return @{
        beHealth     = $beHealth
        bePort       = $bePort
        feUp         = $feUp
        pyExists     = $pyExists
        oursPid      = $oursPid
        oursAlive    = $oursAlive
        foreignCount = $foreignCount
    }
}

function Write-StatusStripFromSnapshot($snap) {
    if (-not $snap) { return }
    $beHealth = $snap.beHealth
    Write-Host ""
    Write-Host "  " -NoNewline
    Write-Host "服务端" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $BackendPort) -NoNewline -ForegroundColor DarkGray
    if ($beHealth.ok) { Write-Host "运行中 " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    elseif ($snap.bePort) { Write-Host "占用中 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    else { Write-Host "未启动 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }
    Write-Host "   " -NoNewline
    Write-Host "运营台" -NoNewline -ForegroundColor DarkGray
    Write-Host (" :{0} " -f $FrontendPort) -NoNewline -ForegroundColor DarkGray
    if ($snap.feUp) { Write-Host "运行中 " -NoNewline -ForegroundColor Green -BackgroundColor DarkGreen }
    else { Write-Host "未启动 " -NoNewline -ForegroundColor Yellow -BackgroundColor DarkYellow }

    if (-not $snap.pyExists) {
        Write-Host "    运行环境未就绪 · 按 N 查看环境自检" -ForegroundColor Red
    } elseif ($beHealth.ok -and $snap.oursAlive) {
        Write-Host "    由本控制台管理" -ForegroundColor DarkGray
    } elseif ($beHealth.ok) {
        Write-Host "    服务已在运行，但非本控制台启动 · 按 2 可接管" -ForegroundColor Yellow
    } elseif ($snap.bePort) {
        Write-Host "    端口被占用，服务尚未正常响应" -ForegroundColor Yellow
        if ([int]$snap.foreignCount -gt 0) {
            Write-Host " · 其他程序占用中（P 查看 · K 释放）" -ForegroundColor Yellow
        }
    } else {
        Write-Host "" -ForegroundColor DarkGray
    }
    if (-not $script:AutoKillOnStart) {
        Write-Host "  启动前清理端口：关" -ForegroundColor Yellow
    }
    if (-not $script:BackendReload) {
        Write-Host "  服务热重载：关" -ForegroundColor Yellow
    }
    if (-not $snap.pyExists -or -not $beHealth.ok) {
        Write-Host "  提示：按 N 进行环境自检" -ForegroundColor DarkGray
    }
}

function Show-StatusStrip {
    Write-StatusStripFromSnapshot (Get-ServiceStatusSnapshot)
}

function Write-MenuHeader {
    Write-Host "  ==============================================" -ForegroundColor DarkCyan
    Write-Host "    " -NoNewline
    Write-Host "毕设港" -NoNewline -ForegroundColor Cyan
    Write-Host "  ·  本地控制台" -ForegroundColor Gray
    Write-Host "  ==============================================" -ForegroundColor DarkCyan
}

function Show-Menu {
    # 每次重绘前锁窗高=缓冲高，避免操作过程中又冒出滚动条
    if (-not $script:CliMode) { Set-ConsoleRemoteSize }
    Clear-Host
    Write-MenuHeader
    Write-Host ""
    Write-Host "  正在检查服务状态…" -ForegroundColor DarkGray

    $snap = Get-ServiceStatusSnapshot

    Clear-Host
    Write-MenuHeader
    Write-StatusStripFromSnapshot $snap

    Write-BlockTitle "服务"
    Write-Pair "1" "启动全部"      "2" "重启服务端" "Cyan" "Cyan"
    Write-Pair "3" "仅服务端"      "4" "仅运营台"
    Write-Pair "5" "全部停止"      "8" "清理重复" "Gray" "Yellow"

    Write-BlockTitle "访问"
    Write-Pair "6" "停服务端"      "7" "停运营台"
    Write-Pair "9" "打开运营台"    "A" "接口文档"
    Write-Pair "B" "健康检查"      "C" "项目目录"
    Write-Pair "D" "工作区"        "E" "上传目录"
    Write-Pair "S" "样例开题"

    Write-BlockTitle "端口 / 选项"
    Write-Pair "P" "端口占用"      "K" "释放端口" "Yellow" "Yellow"
    Write-Pair "T" "启动前清端口"  "U" "服务热重载" "Gray" "Gray"

    Write-BlockTitle "数据库 / 其他"
    Write-Pair "F" "启演示库"      "G" "演示库状态"
    Write-Pair "H" "停演示库"      "R" "刷新"
    Write-Pair "N" "环境自检"      "V" "校验脚本" "Cyan" "Gray"
    Write-Pair "0" "退出" "" "" "DarkGray" "DarkGray"

    Write-Host ""
    Write-Host "  运营台  $UiUrl" -ForegroundColor DarkGray
    Write-Host "  服务端  $ApiUrl" -ForegroundColor DarkGray
    $autoHint = if ($script:AutoKillOnStart) { "清端口：开" } else { "清端口：关" }
    $reloadHint = if ($script:BackendReload) { "热重载：开" } else { "热重载：关" }
    Write-Host ("  选项    {0} · {1}  ·  T/U 切换" -f $autoHint, $reloadHint) -ForegroundColor DarkGray
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
            Write-Line "  正在重启服务端…" "Cyan"
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
            Write-Line "  正在停止全部服务…" "Cyan"
            Stop-FrontendAll
            Stop-BackendAll
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "6" {
            Write-Line "  正在停止服务端…" "Cyan"
            Stop-BackendAll
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "7" {
            Write-Line "  正在停止运营台…" "Cyan"
            Stop-FrontendAll
            Show-StatusStrip
            Flash-ThenContinue
            return "ok"
        }
        "8" {
            Write-Line "  正在清理重复实例…" "Cyan"
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
            Write-Line "  正在释放端口…" "Cyan"
            Stop-PortOccupants $BackendPort "服务端"
            Stop-PortOccupants $FrontendPort "运营台"
            Show-StatusStrip
            Flash-ThenContinue 900
            return "ok"
        }
        "T" {
            $script:AutoKillOnStart = -not $script:AutoKillOnStart
            if ($script:AutoKillOnStart) {
                $env:GF_NO_AUTO_KILL = "0"
                Write-Line ("  启动前清理端口：已开启（下次启动将先释放 :{0}）" -f $BackendPort) "Green"
            } else {
                $env:GF_NO_AUTO_KILL = "1"
                Write-Line "  启动前清理端口：已关闭（占用时请按 P 查看或 K 释放）" "Yellow"
            }
            Flash-ThenContinue 900
            return "ok"
        }
        "U" {
            $script:BackendReload = -not $script:BackendReload
            if ($script:BackendReload) {
                $env:GF_BACKEND_RELOAD = "1"
                Write-Line "  服务热重载：已开启（按 2 重启后生效）" "Green"
            } else {
                $env:GF_BACKEND_RELOAD = "0"
                Write-Line "  服务热重载：已关闭（变更后需按 2 手动重启 · 下次重启后生效）" "Yellow"
            }
            Flash-ThenContinue 1100
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
        "N" {
            [void](Show-EnvDoctor)
            if ($script:CliMode) { return "ok" }
            Pause-Menu "按 Enter 返回菜单..."
            return "ok"
        }
        "B" {
            Write-Line "  正在检查服务健康状态…" "DarkGray"
            $h = Invoke-HealthCheck
            if ($h.ok) { Write-Line "  [正常] 服务端响应正常" "Green" }
            else { Write-Line "  [异常] 服务端无响应" "Red" }
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
            Write-Line "  将停止本地演示库（不影响本机已安装的 MySQL；数据卷默认保留）" "Yellow"
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
            Write-Line "  [提示] 无效：$Choice  （1 启动全部 · 2 重启服务端 · 5 停止全部 · 0 退出）" "Yellow"
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
