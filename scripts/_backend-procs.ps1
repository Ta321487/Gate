# Shared backend process discovery + light venv checks + owned-PID start
# Used by launcher.ps1 / kill-dup-backend.ps1 / start-backend.ps1 (dot-source only)

$script:GfBackendPort = 8000
$script:GfUvicornNeedle = "uvicorn app.main:app"
# Must match scripts/launcher.bat (GF_WT_WINDOW); one name for console + service tabs
$script:GfWtWindow = if ($env:GF_WT_WINDOW) { $env:GF_WT_WINDOW } else { "gf-gate" }

function Get-GfBackendVenvPython {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return (Join-Path $RepoRoot "backend\.venv\Scripts\python.exe")
}

function Get-GfAncestorPids {
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    $result = New-Object System.Collections.Generic.List[int]
    $cur = $ProcessId
    $guard = 0
    while ($cur -and $guard -lt 32) {
        $guard++
        $result.Add($cur)
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$cur" -ErrorAction SilentlyContinue
        if (-not $proc -or -not $proc.ParentProcessId -or $proc.ParentProcessId -eq 0) { break }
        $cur = [int]$proc.ParentProcessId
    }
    return @($result)
}

function Get-GfProtectedBackendPids {
    param([int[]]$ListenPids)
    $protected = @{}
    foreach ($lp in @($ListenPids)) {
        if (-not $lp) { continue }
        foreach ($a in @(Get-GfAncestorPids -ProcessId ([int]$lp))) { $protected[[int]$a] = $true }
        foreach ($d in @(Get-GfDescendantPids -RootPid ([int]$lp))) { $protected[[int]$d] = $true }
    }
    return $protected
}

function Get-GfBackendPidFile {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    return (Join-Path $RepoRoot "backend\.gate_backend.pid")
}

function Save-GfBackendPid {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [Parameter(Mandatory = $true)][int]$ProcessId
    )
    $f = Get-GfBackendPidFile -RepoRoot $RepoRoot
    Set-Content -LiteralPath $f -Value $ProcessId -Encoding Ascii -Force
}

function Read-GfBackendPid {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $f = Get-GfBackendPidFile -RepoRoot $RepoRoot
    if (-not (Test-Path -LiteralPath $f)) { return $null }
    $raw = (Get-Content -LiteralPath $f -Raw -ErrorAction SilentlyContinue)
    if (-not $raw) { return $null }
    $t = $raw.Trim()
    if ($t -match '^\d+$') { return [int]$t }
    return $null
}

function Get-GfDescendantPids {
    param([Parameter(Mandatory = $true)][int]$RootPid)
    $result = New-Object System.Collections.Generic.List[int]
    $queue = New-Object System.Collections.Generic.Queue[int]
    $queue.Enqueue($RootPid)
    $seen = @{}
    while ($queue.Count -gt 0) {
        $cur = $queue.Dequeue()
        if ($seen.ContainsKey($cur)) { continue }
        $seen[$cur] = $true
        $result.Add($cur)
        $children = @(
            Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object { $_.ParentProcessId -eq $cur } |
                Select-Object -ExpandProperty ProcessId
        )
        foreach ($c in $children) { $queue.Enqueue([int]$c) }
    }
    return @($result)
}

function Test-GfOurBackendListening {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [int]$Port = $script:GfBackendPort
    )
    $want = Read-GfBackendPid -RepoRoot $RepoRoot
    if (-not $want) { return $false }

    # Windows venv: Scripts\python.exe often parents a home\python.exe that actually binds
    $tree = @(Get-GfDescendantPids -RootPid $want)
    if ($tree.Count -eq 0) { return $false }

    $listen = @(Get-GfListenPids -Port $Port)
    foreach ($lp in $listen) {
        if ($tree -contains [int]$lp) {
            if ([int]$lp -ne $want) {
                Save-GfBackendPid -RepoRoot $RepoRoot -ProcessId ([int]$lp)
            }
            return $true
        }
    }
    return $false
}

function Start-GfBackendProcess {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [int]$Port = $script:GfBackendPort,
        [switch]$NewWindow
    )
    $py = Get-GfBackendVenvPython -RepoRoot $RepoRoot
    if (-not (Test-Path -LiteralPath $py)) {
        throw "missing venv python: $py"
    }
    $wd = Join-Path $RepoRoot "backend"
    $arg = @(
        "-m", "uvicorn", "app.main:app",
        "--host", "127.0.0.1",
        "--port", "$Port",
        "--no-use-colors"
    )
    # Default: stay in current console (WT tab). Start-Process without -NoNewWindow
    # opens a floating cmd window — that was the bug.
    if ($NewWindow) {
        $p = Start-Process -FilePath $py -ArgumentList $arg -WorkingDirectory $wd -PassThru
    } else {
        $p = Start-Process -FilePath $py -ArgumentList $arg -WorkingDirectory $wd -PassThru -NoNewWindow
    }
    if (-not $p) { throw "Start-Process failed" }
    Save-GfBackendPid -RepoRoot $RepoRoot -ProcessId $p.Id
    return $p
}

function Test-GfCmdUsesRepoVenv {
    param(
        [string]$CommandLine,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return $false }
    $cmd = $CommandLine.ToLowerInvariant().Replace("/", "\")
    $repo = $RepoRoot.ToLowerInvariant().TrimEnd("\").Replace("/", "\")
    if ($cmd -notlike "*$repo*") { return $false }
    return ($cmd -like "*backend\.venv\scripts\python*")
}

function Test-GfProcUsesRepoVenv {
    param(
        $Proc,
        [Parameter(Mandatory = $true)][string]$RepoRoot
    )
    if (-not $Proc) { return $false }
    $ours = Read-GfBackendPid -RepoRoot $RepoRoot
    if ($ours -and ($Proc.ProcessId -eq $ours)) { return $true }
    if (Test-GfCmdUsesRepoVenv -CommandLine $Proc.CommandLine -RepoRoot $RepoRoot) {
        return $true
    }
    $exe = [string]$Proc.ExecutablePath
    if ([string]::IsNullOrWhiteSpace($exe)) { return $false }
    $exeN = $exe.ToLowerInvariant().Replace("/", "\")
    $repo = $RepoRoot.ToLowerInvariant().TrimEnd("\").Replace("/", "\")
    return ($exeN -like "*$repo*backend\.venv\scripts\python*")
}

function Get-GfBackendPythonEnv {
    param(
        [Parameter(Mandatory = $true)][string]$RepoRoot,
        [switch]$CheckImport
    )
    $py = Get-GfBackendVenvPython -RepoRoot $RepoRoot
    $out = [pscustomobject]@{
        ok      = $false
        exists  = $false
        uvicorn = $null
        python  = $py
        message = ""
    }
    if (-not (Test-Path -LiteralPath $py)) {
        $out.message = "missing backend\.venv\Scripts\python.exe (create venv and install deps)"
        return $out
    }
    $out.exists = $true
    if ($CheckImport) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $null = & $py -c "import uvicorn" 2>&1
        $code = $LASTEXITCODE
        $ErrorActionPreference = $prevEap
        if ($code -ne 0) {
            $out.uvicorn = $false
            $out.message = "venv found but cannot import uvicorn (pip install -r requirements.txt)"
            return $out
        }
        $out.uvicorn = $true
    }
    $out.ok = $true
    $out.message = "backend\.venv OK"
    return $out
}

function Get-GfListenPids {
    param([int]$Port = $script:GfBackendPort)
    try {
        return @(
            Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
                Select-Object -ExpandProperty OwningProcess -Unique
        )
    } catch {
        return @()
    }
}

function Get-GfPortOccupants {
    <#
    .SYNOPSIS
      Who is listening on LocalPort (pid / name / cmdline). Optional Ours via pidfile tree.
    #>
    param(
        [Parameter(Mandatory = $true)][int]$Port,
        [string]$RepoRoot = "",
        [int]$OurRootPid = 0
    )
    $listen = @(Get-GfListenPids -Port $Port)
    if ($listen.Count -eq 0) { return @() }

    $ourTree = @{}
    if ($OurRootPid -gt 0) {
        foreach ($id in @(Get-GfDescendantPids -RootPid $OurRootPid)) {
            $ourTree[[int]$id] = $true
        }
    } elseif ($RepoRoot -and (Test-Path -LiteralPath $RepoRoot)) {
        $want = Read-GfBackendPid -RepoRoot $RepoRoot
        if ($want) {
            foreach ($id in @(Get-GfDescendantPids -RootPid $want)) {
                $ourTree[[int]$id] = $true
            }
        }
    }

    $out = New-Object System.Collections.Generic.List[object]
    foreach ($listenPid in $listen) {
        if (-not $listenPid) { continue }
        $id = [int]$listenPid
        $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
        $name = if ($cim) { [string]$cim.Name } else {
            $gp = Get-Process -Id $id -ErrorAction SilentlyContinue
            if ($gp) { $gp.ProcessName } else { "?" }
        }
        $cmd = if ($cim -and $cim.CommandLine) {
            ($cim.CommandLine -replace "\s+", " ").Trim()
        } else { "" }
        if ($cmd.Length -gt 140) { $cmd = $cmd.Substring(0, 140) + "..." }
        $ours = $ourTree.ContainsKey($id)
        $out.Add([pscustomobject]@{
            Pid     = $id
            Name    = $name
            Cmd     = $cmd
            Ours    = [bool]$ours
            Port    = $Port
        })
    }
    return @($out.ToArray())
}

function Test-GfPythonProcessName {
    param([string]$Name)
    return [bool]($Name -match '^(python|pythonw)(\.exe)?$')
}

function Get-GfPythonTreeRoot {
    <#
    .SYNOPSIS
      Walk up while parent is still python/pythonw.
      venv Scripts\python.exe often re-execs to home python.exe; the listener sits on the
      child, and taskkill /T on that child commonly returns Access Denied. Kill the
      outermost python (venv parent) instead.
    #>
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    $cur = [int]$ProcessId
    $guard = 0
    while ($cur -gt 0 -and $guard -lt 16) {
        $guard++
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$cur" -ErrorAction SilentlyContinue
        if (-not $proc) { break }
        $ppid = [int]$proc.ParentProcessId
        if ($ppid -le 0) { break }
        $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$ppid" -ErrorAction SilentlyContinue
        if (-not $parent -or -not (Test-GfPythonProcessName -Name $parent.Name)) { break }
        $cur = $ppid
    }
    return $cur
}

function Invoke-GfTaskkill {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [switch]$Tree
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    if ($Tree) {
        $raw = & taskkill.exe /PID $ProcessId /T /F 2>&1
    } else {
        $raw = & taskkill.exe /PID $ProcessId /F 2>&1
    }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    # Drop RemoteException noise; keep ERROR: lines from taskkill
    $text = @(
        $raw | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { "$_" }
        } | Where-Object { $_ -and ($_ -notmatch 'RemoteException') }
    ) -join " "
    return [pscustomobject]@{
        code = [int]$code
        text = $text.Trim()
    }
}

function Test-GfTaskkillOk {
    param($Result)
    return ($Result.code -eq 0 -or $Result.code -eq 128)
}

function Stop-GfProcessTree {
    # Prefer outermost python (venv parent). Listener is often the re-exec child;
    # taskkill /T on that child → Access Denied; /T on parent or /F on child works.
    # Exit 128 = process already gone (treat as ok).
    param([Parameter(Mandatory = $true)][int]$ProcessId)
    $out = [pscustomobject]@{
        ok      = $false
        message = ""
    }
    if ($ProcessId -le 0) {
        $out.message = "invalid pid"
        return $out
    }

    $root = Get-GfPythonTreeRoot -ProcessId $ProcessId
    $candidates = @($root, $ProcessId) | Select-Object -Unique

    foreach ($id in $candidates) {
        $r = Invoke-GfTaskkill -ProcessId $id -Tree
        if (Test-GfTaskkillOk $r) {
            Start-Sleep -Milliseconds 150
            if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
                $out.ok = $true
                $out.message = if ($id -ne $ProcessId) {
                    "killed via parent pid=$id"
                } elseif ($r.code -eq 128) {
                    "already gone"
                } else {
                    "killed"
                }
                return $out
            }
        }
    }

    # /T on re-exec child often Access Denied; plain /F usually works
    foreach ($id in $candidates) {
        if (-not (Get-Process -Id $id -ErrorAction SilentlyContinue)) { continue }
        $r = Invoke-GfTaskkill -ProcessId $id
        if (Test-GfTaskkillOk $r) {
            Start-Sleep -Milliseconds 150
            if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
                $out.ok = $true
                $out.message = "killed (no-tree)"
                return $out
            }
        }
    }

    if (-not (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) {
        $out.ok = $true
        $out.message = "already gone"
        return $out
    }

    # Keep ASCII: Windows PowerShell 5.1 reads this file as system ANSI without BOM.
    $out.message = "Access denied (venv child?). Retry K, or close the backend window."
    return $out
}

function Get-GfTreeRootPids {
    # Among a pid set, keep only roots (parent not in the set). Kill these with /T.
    param([int[]]$ProcessIds)
    $set = @{}
    foreach ($id in @($ProcessIds)) {
        if ($id -gt 0) { $set[[int]$id] = $true }
    }
    $roots = New-Object System.Collections.Generic.List[int]
    foreach ($id in @($set.Keys)) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$id" -ErrorAction SilentlyContinue
        $ppid = if ($proc) { [int]$proc.ParentProcessId } else { 0 }
        if ($ppid -le 0 -or -not $set.ContainsKey($ppid)) {
            $roots.Add([int]$id)
        }
    }
    return @($roots | Sort-Object)
}

function Get-GfBackendProcs {
    param([int]$Port = $script:GfBackendPort)
    $needle = $script:GfUvicornNeedle
    $byCmd = @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '^(python|pythonw)(\.exe)?$' -and
                $_.CommandLine -and
                $_.CommandLine -like "*$needle*"
            }
    )
    $listenPids = @(Get-GfListenPids -Port $Port)
    $byPort = @()
    if ($listenPids.Count -gt 0) {
        $byPort = @(
            Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
                Where-Object {
                    $listenPids -contains $_.ProcessId -and
                    $_.Name -match '^(python|pythonw)(\.exe)?$'
                }
        )
    }
    $merged = @{}
    foreach ($p in ($byCmd + $byPort)) {
        if ($p -and -not $merged.ContainsKey($p.ProcessId)) {
            $merged[$p.ProcessId] = $p
        }
    }
    return @{
        Procs      = @($merged.Values | Sort-Object CreationDate)
        ListenPids = $listenPids
    }
}