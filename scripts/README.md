# scripts

Windows 启动与运维脚本。**约定：bat 只做入口，ps1 做逻辑。**

## 入口

| 脚本 | 用途 |
|------|------|
| `launcher.bat` | **推荐** 控制台菜单；有 Windows Terminal 时进 WT，服务用同窗标签页 |
| `start-backend.bat` | 仅启动后端 `:8000`（独立窗口） |
| `start-frontend.bat` | 仅启动前端 `:5300`（避开学生包 `:5173`） |
| `stop-backend.bat` | 停止全部 uvicorn 后端 |
| `stop-frontend.bat` | 停止 `:5300` 监听进程 |
| `kill-dup-backend.bat` | 清理重复 uvicorn（默认保留最新；`/all` 全杀） |
| `verify-scripts.bat` | **编码门禁**：`.bat` 纯 ASCII 无 BOM、`.ps1` 带 UTF-8 BOM，并用 5.1 解析器验语法；`-Fix` 自动补/去 BOM |
| `verify-bats.bat` | 旧入口别名（等价 `verify-scripts.bat`，只保留兼容） |
| `setup-cn-mirrors.ps1` | 国内镜像一键配置（pip / npm / Maven / Docker，**用户级**） |
| `start-aoci-ui.vbs` | **推荐** 启动本仓库 AOCI 面板（无窗口） |
| `stop-aoci-ui.vbs` | 停止本仓库已登记的 AOCI 面板 |

对应的 `.bat` 只转给同名 `.vbs`，`.ps1` 才真正调 `aoci.exe`。不要直接跑 `aoci ui`。

## 控制台键位（高频优先）

| 键 | 作用 |
|----|------|
| `1` | 启动全部服务（服务端 + 运营台） |
| `2` | 重启服务端 |
| `3` / `4` | 仅启动服务端 / 仅启动运营台 |
| `5` | 停止全部服务 |
| `6` / `7` | 停止服务端 / 停止运营台 |
| `8` | 清理重复实例 |
| `9` / `A` | 打开运营台 / 接口文档 |
| `N` | 环境自检 |
| `R` | 刷新状态 |
| `T` | 启动前清理端口 开/关 |
| `U` | 服务热重载 开/关（需再按 `2` 重启生效） |
| `0` | 退出 |

环境变量：`GF_NO_AUTO_KILL=1` 默认关闭「启动前清理端口」；`GF_BACKEND_RELOAD=0` 默认关闭「服务热重载」。

启停后**自动回菜单**（不必再按 Enter）。健康检查 / Compose / 查编码仍会停一下方便看输出。

### 命令行直达（不开菜单）

```bat
scripts\launcher.bat 1
scripts\launcher.bat 2
scripts\launcher.bat 5
scripts\launcher.bat restart
scripts\launcher.bat both
scripts\launcher.bat stop
```

## 编码（重要）

| 类型 | 编码 | 内容 |
|------|------|------|
| `.bat` | **纯 ASCII**，无 BOM | `@echo off`、`if`、`call` 等 |
| `.vbs` | **纯 ASCII** | 隐藏窗口拉起对应 `.ps1` |
| `.ps1` | **UTF-8 with BOM** | 中文菜单、进程检测、Docker 等 |

**不要把中文写进 `.bat`。** cmd 默认 GBK；若 bat 带 UTF-8 BOM，会出现 `错缀echo`、`f not exist` 等乱执行。

**为什么 `.ps1` 必须带 BOM。** Windows PowerShell 5.1（`launcher.bat` 调的就是它）把无 BOM 的 UTF-8 当 GBK 解码；中文字符串末尾的字节可能把 `"` 当成双字节的尾字节吞掉，字符串从此不闭合，随后整段 C# 被当 PowerShell 语句解析，报一串 `缺少 using 指令` / `意外的属性 DllImport`。PowerShell 7 无 BOM 也能读，所以问题只在双击 `.bat` 走 5.1 时才暴露——`launcher.ps1` 就这样崩过一次（2026-11-23 批量重写丢了 BOM）。

改完 `.bat` 或 `.ps1` 都跑一遍门禁：

```bat
scripts\verify-scripts.bat          :: 检查（含 5.1 语法解析）
scripts\verify-scripts.bat -Fix     :: 能自动修的修掉：.bat 去 BOM / .ps1 补 BOM
```

`scripts\verify-bats.bat` 是旧别名，行为完全一样。控制台菜单 `V` 调的也是这条门禁。

## Windows Terminal 标签页

- 双击 / 运行 `launcher.bat`：若已装 Windows Terminal，会进 **一个较窄的 WT 窗口**（约 52×36，缓冲与窗同高、无竖向滚动条）跑本地控制台。
- 菜单 `1` / `2` / `3` / `4`：在同窗 **新标签** 里跑服务（不是再弹一堆独立窗口）。
- 直接双击 `start-backend.bat` / `start-frontend.bat`：仍是 **独立窗口**（不变）。
- 强制旧行为：启动前设环境变量 `GF_LAUNCH_STYLE=window`。

## AOCI 面板

双击 `start-aoci-ui.vbs` / `stop-aoci-ui.vbs`。脚本把仓库根解析为 `scripts` 的上一级，并在启动前把 `scripts\aoci-git-shim` 放到 `PATH` 最前。

| 文件 | 作用 |
|------|------|
| `start-aoci-ui.vbs` | 隐藏窗口拉起 `start-aoci-ui.ps1` |
| `start-aoci-ui.ps1` | `aoci ui --detach`，打开打印出的本机地址 |
| `stop-aoci-ui.ps1` | `aoci ui --stop` |
| `aoci-git-shim\git.exe` | 无控制台转发本机 git；`ls-files --others --ignored` 直接返回空 |

Windows 上每次拉起 `Git\cmd\git.exe` 都会闪空白控制台。面板会反复扫忽略文件，所以必须走这套包装。

已有面板在跑时，`--detach` **复用旧进程**，不会换上这次的 `PATH`。再闪就先 `stop-aoci-ui.vbs`，再 `start-aoci-ui.vbs`。

`aoci-git-shim\git-shim.cs` 是包装源码；改完需用 `csc /target:winexe` 重编 `git.exe`。日常启动不用编译。

## Compose 数据库

菜单 `F` / `G` / `H` 管的是仓库根目录 `docker-compose.yml` 里的 **MySQL 容器**，不是 Windows 本机 **MySQL80** 服务。需要已安装并运行 Docker Desktop。

## 国内镜像（可选）

首次装环境若 pip / npm / Maven / Docker 拉取很慢，可跑：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup-cn-mirrors.ps1
```

会写入**当前用户**的 pip、`.npmrc` / `.pnpmrc` / `.yarnrc`、`.m2/settings.xml`、`.docker/daemon.json`（覆盖已有配置）。Docker 改完需在 Desktop 里重启一次。
