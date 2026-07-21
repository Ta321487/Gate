# scripts

Windows 启动与运维脚本。**约定：bat 只做入口，ps1 做逻辑。**

## 入口

| 脚本 | 用途 |
|------|------|
| `launcher.bat` | **推荐** 控制台菜单（起停 / 打开目录 / Compose / 健康检查）；有 Windows Terminal 时进 WT，服务用同窗标签页 |
| `start-backend.bat` | 仅启动后端 `:8000` |
| `start-frontend.bat` | 仅启动前端 `:5173` |
| `stop-backend.bat` | 停止全部 uvicorn 后端 |
| `stop-frontend.bat` | 停止 `:5173` 监听进程 |
| `kill-dup-backend.bat` | 清理重复 uvicorn（默认保留最新；`/all` 全杀） |
| `verify-bats.bat` | 检查 bat 是否误存为 UTF-8 BOM / 含中文 |

## 编码（重要）

| 类型 | 编码 | 内容 |
|------|------|------|
| `.bat` | **纯 ASCII**，无 BOM | `@echo off`、`if`、`call` 等 |
| `.ps1` | **UTF-8 with BOM** | 中文菜单、进程检测、Docker 等 |

**不要把中文写进 `.bat`。** cmd 默认 GBK；若 bat 带 UTF-8 BOM，会出现 `错缀echo`、`f not exist` 等乱执行。

改完 bat 可跑：

```bat
scripts\verify-bats.bat
```

## Windows Terminal 标签页

- 双击 / 运行 `launcher.bat`：若已装 Windows Terminal，会进 **一个 WT 窗口**跑 Gate 控制台。
- 菜单 `[1]` / `[2]` / `[3]` / `[8]`：在同窗 **新标签** 里跑 `start-*.bat`（cmd），不是再弹一堆独立窗口。
- 直接双击 `start-backend.bat` / `start-frontend.bat`：仍是 **独立窗口**（不变）。
- 强制旧行为：启动前设环境变量 `GF_LAUNCH_STYLE=window`。

## Compose 数据库

菜单 `[F/G/H]` 管的是仓库根目录 `docker-compose.yml` 里的 **MySQL 容器**，不是 Windows 本机 **MySQL80** 服务。需要已安装并运行 Docker Desktop。
