# 国内镜像一键配置（Windows，用户级）
# 用法：powershell -ExecutionPolicy Bypass -File scripts\setup-cn-mirrors.ps1

$ErrorActionPreference = 'Stop'

Write-Host ">>> 配置 pip（清华源）..."
New-Item -ItemType Directory -Force -Path "$env:APPDATA\pip" | Out-Null
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set global.trusted-host pypi.tuna.tsinghua.edu.cn

Write-Host ">>> 配置 npm / pnpm / yarn（npmmirror）..."
$npmrc = @"
registry=https://registry.npmmirror.com
disturl=https://npmmirror.com/dist
electron_mirror=https://npmmirror.com/mirrors/electron/
sass_binary_site=https://npmmirror.com/mirrors/node-sass/
phantomjs_cdnurl=https://npmmirror.com/mirrors/phantomjs/
chromedriver_cdnurl=https://npmmirror.com/mirrors/chromedriver/
operadriver_cdnurl=https://npmmirror.com/mirrors/operadriver/
"@
Set-Content -Path "$env:USERPROFILE\.npmrc" -Value $npmrc.TrimEnd() -Encoding UTF8
Set-Content -Path "$env:USERPROFILE\.pnpmrc" -Value "registry=https://registry.npmmirror.com" -Encoding UTF8
Set-Content -Path "$env:USERPROFILE\.yarnrc" -Value 'registry "https://registry.npmmirror.com"' -Encoding UTF8

Write-Host ">>> 配置 Maven（阿里云）..."
$m2 = Join-Path $env:USERPROFILE '.m2'
New-Item -ItemType Directory -Force -Path $m2 | Out-Null
@'
<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.2.0 https://maven.apache.org/xsd/settings-1.2.0.xsd">
  <mirrors>
    <mirror>
      <id>aliyunmaven</id>
      <mirrorOf>*</mirrorOf>
      <name>阿里云公共仓库</name>
      <url>https://maven.aliyun.com/repository/public</url>
    </mirror>
  </mirrors>
</settings>
'@ | Set-Content -Path (Join-Path $m2 'settings.xml') -Encoding UTF8

Write-Host ">>> 配置 Docker Desktop 镜像加速..."
$dockerDir = Join-Path $env:USERPROFILE '.docker'
New-Item -ItemType Directory -Force -Path $dockerDir | Out-Null
@'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
'@ | Set-Content -Path (Join-Path $dockerDir 'daemon.json') -Encoding UTF8

Write-Host ""
Write-Host "完成。已写入："
Write-Host "  pip     -> $env:APPDATA\pip\pip.ini"
Write-Host "  npm     -> $env:USERPROFILE\.npmrc"
Write-Host "  pnpm    -> $env:USERPROFILE\.pnpmrc"
Write-Host "  yarn    -> $env:USERPROFILE\.yarnrc"
Write-Host "  Maven   -> $env:USERPROFILE\.m2\settings.xml"
Write-Host "  Docker  -> $env:USERPROFILE\.docker\daemon.json"
Write-Host ""
Write-Host "提示：Node / Maven / Docker 安装后会自动生效；Docker 需在 Desktop 设置里重启一次。"
