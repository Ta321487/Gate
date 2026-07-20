# scripts

Windows 启动与运维脚本。**约定：bat 只做入口，ps1 做逻辑。**

## 入口

| 脚本 | 用途 |
|------|------|
| `launcher.bat` | **推荐** 控制台菜单（起停 / 打开目录 / Compose / 健康检查） |
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

## Compose 数据库

菜单 `[F/G/H]` 管的是仓库根目录 `docker-compose.yml` 里的 **MySQL 容器**，不是 Windows 本机 **MySQL80** 服务。需要已安装并运行 Docker Desktop。
