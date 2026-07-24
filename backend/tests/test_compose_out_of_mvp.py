"""compose_out_of_mvp：本期不做随目录+开题合成，非写死。"""

from app.bake.capabilities import compose_out_of_mvp
from app.bake.domain_schema import attach_accept


def test_empty_proposal_keeps_domain_defaults():
    items = compose_out_of_mvp("DOM-ATTEND", "")
    assert "人脸考勤" in items
    assert "GPS轨迹打卡" in items


def test_long_proposal_drops_unrelated_defaults():
    text = (
        "本系统实现学生请假申请、审批与销假台账管理。"
        "用户提交请假单，管理员审核通过或驳回，销假后完结。"
        "主要功能包括人员档案、请假记录与公告管理。" * 2
    )
    assert len(text) >= 80
    items = compose_out_of_mvp("DOM-ATTEND", text, scanned_signals=[])
    assert "人脸考勤" not in items
    assert "GPS轨迹打卡" not in items


def test_long_proposal_keeps_mentioned_default():
    text = (
        "本系统实现请假审批与销假；本期不做人脸考勤与硬件对接。"
        "用户提交请假单，管理员审核，形成假勤台账。" * 3
    )
    items = compose_out_of_mvp("DOM-ATTEND", text, scanned_signals=[])
    assert "人脸考勤" in items


def test_scanned_signals_always_merged():
    items = compose_out_of_mvp(
        "DOM-RECRUIT",
        "招聘岗位发布与简历投递审核系统，主要功能是岗位与投递。" * 4,
        scanned_signals=["视频面试"],
    )
    assert "视频面试" in items
    # 题面未提 ATS → 默认项应被收窄掉
    assert "ATS爬虫导入" not in items


def test_attach_accept_writes_composed_out_of_mvp():
    spec = {
        "domain": "DOM-ATTEND",
        "title": "学生请假管理系统",
        "archetype": "ARCH-FLOW",
        "features": [
            {"name": "请假审批", "status": "flow"},
            {"name": "人脸考勤", "status": "out_of_mvp"},
        ],
        "out_of_mvp": ["人脸考勤", "GPS轨迹打卡"],
    }
    text = (
        "学生请假管理系统：提交请假、审批、销假与公告。"
        "不涉及人脸识别与轨迹定位。" * 3
    )
    out = attach_accept(spec, text)
    assert "out_of_mvp" in out
    assert isinstance(out["out_of_mvp"], list)
    # 题面提到人脸 → 保留相关默认；GPS 未提则可不出现
    assert "人脸考勤" in out["out_of_mvp"] or any(
        "人脸" in x for x in out["out_of_mvp"]
    )
    oos_feats = [
        f["name"]
        for f in out["features"]
        if isinstance(f, dict) and f.get("status") == "out_of_mvp"
    ]
    assert oos_feats
    assert "请假审批" in {
        f["name"] for f in out["features"] if isinstance(f, dict)
    }
