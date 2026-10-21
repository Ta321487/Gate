#!/usr/bin/env pwsh
# 以 .cursor/rules 为权威源，把规则同步到 .trae/rules（.mdc -> .md，正文原样）。
# 规则只在 .cursor/rules 改，改完跑本脚本；不要在 .trae/rules 手改，否则会漂移。
$ErrorActionPreference = 'Stop'
$root = Resolve-Path (Join-Path $PSScriptRoot '..')
$src = Join-Path $root '.cursor/rules'
$dst = Join-Path $root '.trae/rules'
New-Item -ItemType Directory -Path $dst -Force | Out-Null
$utf8 = New-Object Text.UTF8Encoding($false)
Get-ChildItem -LiteralPath $src -File -Filter *.mdc | ForEach-Object {
  $content = [IO.File]::ReadAllText($_.FullName)
  $target = Join-Path $dst ($_.BaseName + '.md')
  [IO.File]::WriteAllText($target, $content, $utf8)
  Write-Host "synced $($_.BaseName)"
}
Write-Host "done: $((Get-ChildItem -LiteralPath $src -File -Filter *.mdc).Count) rules -> $dst"
