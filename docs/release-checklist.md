# 发版检查单（产品化 C2 / F2）

> 声称「无人值守」或合入可运行主线前勾选。日期写入 HANDOFF「发版」段。

## 最小检查（必勾）

| # | 项 | 命令 / 动作 | 通过 |
|---|-----|-------------|------|
| 1 | Canary 组代表门禁 | `cd backend && .\.venv\Scripts\python.exe -m pytest -q tests/test_audit_group_canaries.py` | [ ] |
| 2 | 控制台写后契约 | `pytest -q tests/test_console_write_after_contract.py tests/test_delivery_readiness_contract.py tests/test_delivery_stages_contract.py tests/test_delivery_workbench_contract.py` | [ ] |
| 3 | 合卷/匹配冒烟 | 真机：匹配确认 → 生成 → 质检交付验收 → 重打包 → 下载（或明确阻断） | [ ] |
| 4 | 文档索引 | `docs/README.md` / `product-form-maturity.md` §5.1 状态与 HANDOFF 一致 | [ ] |
| 5 | IDE 规则双份 | 若改过 `.cursor/rules`：跑 `scripts/sync-ide-rules.ps1` | [ ] |
| 6 | 安装前置（M1） | 新机：JDK17 / Node18+ / Maven / MySQL8 / `scripts\launcher.bat`；对照 README「环境要求」≤30min 起得来 | [ ] |
| 7 | 材料图抽检（D1） | 抽 ≥1 域打开模块图/E-R：无严重重叠；失败卡可打开 findings（非假可导出） | [ ] |
| 8 | 整厂产品形态 | 声称产品形态收口前：[`product-form-maturity.md`](./product-form-maturity.md) §2.4.5 W1～W15 已勾；口令 `整厂产品形态验收`；证据 [`acceptance/product-form-2026-11-07.md`](./acceptance/product-form-2026-11-07.md) | [x] |
| 9 | 收卡片墙（观感） | 声称「含观感产品完工」前：[`console-product-surface.md`](./console-product-surface.md) V1～V8 已勾；口令 `收卡片墙验收`；证据 [`acceptance/console-surface-2026-11-07.md`](./acceptance/console-surface-2026-11-07.md) | [x] |

## Canary bake（可选加严）

```bat
cd backend
.\.venv\Scripts\python.exe scripts\probe_three_persistence_bake_compile.py --canary
```

## 记录模板（贴进 HANDOFF）

```
发版检查 · YYYY-MM-DD
- canary 门禁：绿 / 红（附用例名）
- 控制台契约：绿 / 红
- 真机冒烟：通过 / 阻断原因
- 检查人：
```
