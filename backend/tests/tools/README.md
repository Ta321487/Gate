# tests/tools

工厂压测 / 一次性检查（可入库，与正规 `test_*.py` 分开）。

```bash
cd backend
python tests/tools/stress_real_topics.py
python tests/tools/peek_match.py
```

公共断言工具在 `tests/helpers/`（如 `normalize`）。
