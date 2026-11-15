"""序列图 → 论文用「工作流程」自然语言（确定性，跨域）。

真源：本张序列图的 messages + participants，禁止套示例范文腔、禁止发明图上没有的步骤。
"""

from __future__ import annotations

from typing import Any


def _clean_action(text: str) -> str:
    t = str(text or "").strip()
    if t.endswith("()") or t.endswith("（）"):
        t = t[:-2].rstrip()
    return t


def _slot_labels(diagram: dict[str, Any]) -> dict[str, str]:
    out = {"actor": "用户", "page": "页面", "controller": "控制器", "db": "数据库"}
    for p in diagram.get("participants") or []:
        if not isinstance(p, dict):
            continue
        pid = str(p.get("id") or "").strip()
        lab = str(p.get("label") or "").strip()
        if pid and lab:
            out[pid] = lab
    return out


def _topic_title(diagram: dict[str, Any]) -> str:
    raw = str(diagram.get("figure_title") or diagram.get("title") or "").strip()
    if raw.endswith("序列图"):
        raw = raw[: -len("序列图")].rstrip()
    return raw or "本功能"


def _sentence_for_message(
    msg: dict[str, Any],
    *,
    labels: dict[str, str],
) -> str:
    frm = str(msg.get("from") or msg.get("frm") or "").strip()
    to = str(msg.get("to") or "").strip()
    direction = str(msg.get("dir") or msg.get("direction") or "").strip()
    action = _clean_action(str(msg.get("text") or ""))
    if not action:
        return ""

    fl = labels.get(frm, frm or "一方")
    tl = labels.get(to, to or "另一方")

    # 页内自调用：写成用户在页面上的操作，避免「页面向页面」
    if frm == to == "page" or direction == "self" and frm == "page":
        return f"{labels.get('actor', '用户')}在页面上{action}。"
    if frm == to == "controller" or (direction == "self" and frm == "controller"):
        return f"控制器{action}。"

    if direction == "response" or (
        direction != "request"
        and direction != "self"
        and (
            (frm == "db" and to == "controller")
            or (frm == "controller" and to == "page")
            or (frm == "page" and to == "actor")
        )
    ):
        if frm == "db" and to == "controller":
            return f"数据库{action}。"
        if frm == "controller" and to == "page":
            return f"控制器向页面{action}。"
        if frm == "page" and to == "actor":
            return f"页面向{tl}反馈：{action}。"
        return f"{fl}向{tl}{action}。"

    # request
    if frm == "actor" and to == "page":
        return f"{fl}在页面上{action}。"
    if frm == "page" and to == "controller":
        return f"页面向控制器发出请求：{action}。"
    if frm == "controller" and to == "db":
        return f"控制器向数据库{action}。"
    return f"{fl}向{tl}{action}。"


def workflow_prose_from_diagram(diagram: dict[str, Any] | None) -> dict[str, Any]:
    """由单张序列图生成工作流说明。"""
    diagram = diagram if isinstance(diagram, dict) else {}
    labels = _slot_labels(diagram)
    topic = _topic_title(diagram)
    heading = f"{topic}的工作流程如下："

    steps: list[dict[str, Any]] = []
    for msg in diagram.get("messages") or []:
        if not isinstance(msg, dict):
            continue
        sent = _sentence_for_message(msg, labels=labels)
        if not sent:
            continue
        # 合并连续完全相同句，避免登录成功类重复感过强时仍保留逐步（序号跟图）
        steps.append(
            {
                "n": len(steps) + 1,
                "seq": int(msg.get("seq") or len(steps) + 1),
                "text": sent,
                "from": str(msg.get("from") or msg.get("frm") or ""),
                "to": str(msg.get("to") or ""),
            }
        )

    lines = [f"（{s['n']}）{s['text']}" for s in steps]
    plain = heading + "\n" + "\n".join(lines) if lines else heading
    return {
        "title": heading,
        "topic": topic,
        "steps": steps,
        "plain": plain,
        "source_note": "由本张序列图消息逐步改写，不发明图外步骤；换题随交付菜单与勾选变化。",
    }


def attach_workflow_to_diagrams(model: dict[str, Any] | None) -> dict[str, Any]:
    """就地给 model.diagrams[*] 挂 workflow。"""
    model = model if isinstance(model, dict) else {}
    diagrams = model.get("diagrams")
    if not isinstance(diagrams, list):
        return model
    for d in diagrams:
        if isinstance(d, dict):
            d["workflow"] = workflow_prose_from_diagram(d)
    return model
