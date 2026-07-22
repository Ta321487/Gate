"""一次性修正 schema 字段 type：金额→number，分类→select，播放链接→url。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fix_text(text: str) -> str:
    money = ("元", "单价", "价格", "费用", "房价", "挂号费")

    def fix_author(m: re.Match) -> str:
        label = m.group(1)
        if any(k in label for k in money):
            return '{"key": "author", "label": "%s", "type": "number"}' % label
        return m.group(0)

    text = re.sub(
        r'\{"key": "author", "label": "([^"]+)", "type": "string"\}',
        fix_author,
        text,
    )
    text = re.sub(
        r'\{"key": "category", "label": "([^"]+)", "type": "string"\}',
        r'{"key": "category", "label": "\1", "type": "select"}',
        text,
    )
    text = text.replace(
        '{"key": "isbn", "label": "播放链接", "type": "string"}',
        '{"key": "isbn", "label": "播放链接", "type": "url"}',
    )
    return text


def main() -> None:
    for rel in (
        "app/bake/schema/templates.py",
        "app/bake/archetype_shells.py",
    ):
        path = ROOT / rel
        old = path.read_text(encoding="utf-8")
        new = fix_text(old)
        # GENERIC 壳：单价/费用类 author
        if "archetype_shells" in rel:
            new = new.replace(
                '{"key": "author", "label": "单价(元)/摘要", "type": "string"}',
                '{"key": "author", "label": "单价(元)", "type": "number"}',
            )
            new = new.replace(
                '{"key": "author", "label": "费用/负责人", "type": "string"}',
                '{"key": "author", "label": "费用(元)", "type": "number"}',
            )
            new = new.replace(
                '{"key": "category", "label": "分类", "type": "string"}',
                '{"key": "category", "label": "分类", "type": "select"}',
            )
        path.write_text(new, encoding="utf-8")
        print(path.name, "done")


if __name__ == "__main__":
    main()
