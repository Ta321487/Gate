"""岗位/角色显示名：开题扫词原样；重绑保留已有 label。"""

from app.bake.staff_posts import attach_staff_posts, staff_posts_for_domain


def _label(domain: str, post_id: str, text: str = "") -> str | None:
    for p in staff_posts_for_domain(domain, proposal_text=text):
        if p.get("id") == post_id:
            return str(p.get("label") or "")
    return None


def test_intern_default_label():
    assert _label("DOM-INTERN", "intern_tutor") == "实习辅导员"


def test_intern_label_from_enterprise_tutor():
    text = "主要功能：学生提交周报，企业导师在线审阅通过或退回。"
    assert _label("DOM-INTERN", "intern_tutor", text) == "企业导师"


def test_intern_enterprise_beats_fudaoyuan_when_both():
    """aliases 顺序：企业导师优先于辅导员。"""
    text = "企业导师审核周报；辅导员协助通知。"
    assert _label("DOM-INTERN", "intern_tutor", text) == "企业导师"


def test_event_duty_label_from_suifangyuan():
    text = "社区公卫：居民上报后由随访员复核处置。"
    assert _label("DOM-EVENT", "duty_clerk", text) == "随访员"


def test_food_rider_label_peisongyuan():
    text = "档口接单后由配送员送到宿舍楼下。"
    posts = staff_posts_for_domain("DOM-FOOD", proposal_text=text)
    by_id = {p["id"]: p["label"] for p in posts}
    assert by_id.get("rider") == "配送员"


def test_attach_preserves_island_label_without_proposal():
    schema = {
        "roles": {
            "user": {"id": "user", "label": "学生"},
            "admin": {"id": "admin", "label": "总管"},
            "subadmin": {"id": "subadmin", "label": "企业导师", "staffPostId": "intern_tutor"},
            "staff_posts": [
                {
                    "id": "intern_tutor",
                    "label": "企业导师",
                    "kind": "clerk",
                    "packs": ["ticket_ops"],
                }
            ],
        }
    }
    out = attach_staff_posts(schema, "DOM-INTERN", proposal_text="")
    posts = out["roles"]["staff_posts"]
    assert posts[0]["label"] == "企业导师"
    assert out["roles"]["subadmin"]["label"] == "企业导师"


def test_attach_user_label_from_proposal():
    schema = {
        "roles": {
            "user": {"id": "user", "label": "用户"},
            "admin": {"id": "admin", "label": "主管（总管）"},
        }
    }
    out = attach_staff_posts(
        schema,
        "DOM-INTERN",
        proposal_text="实习生每周提交周报，辅导员审阅。",
    )
    assert out["roles"]["user"]["label"] == "实习生"
    assert out["roles"]["staff_posts"][0]["label"] == "辅导员"
