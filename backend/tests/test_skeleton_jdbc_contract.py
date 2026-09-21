"""骨架契约：JdbcSupport / AdminAuth 调用面不得再写错。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE_JAVA = ROOT / "skeletons/baseline/backend/src/main/java"
JPA_JAVA = ROOT / "skeletons/overlays/persistence-jpa/backend/src/main/java"
MB_JAVA = ROOT / "skeletons/overlays/persistence-mybatis/backend/src/main/java"

_FORBIDDEN_JDBC_CALLS = (
    "JdbcSupport.get(",
    "JdbcSupport.getJdbcTemplate(",
)
_FORBIDDEN_AUTH = "String uid = AdminAuth.requireAdmin("


def _java_files(*roots: Path) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root.is_dir():
            out.extend(root.rglob("*.java"))
    return out


def test_jdbc_support_only_exposes_jdbc() -> None:
    text = (BASE_JAVA / "com/thesis/config/JdbcSupport.java").read_text(encoding="utf-8")
    assert "public static JdbcTemplate jdbc()" in text
    assert "getJdbcTemplate" not in text
    assert "static JdbcTemplate get(" not in text


def test_no_wrong_jdbc_support_calls_in_skeletons() -> None:
    bad: list[str] = []
    for path in _java_files(BASE_JAVA, JPA_JAVA, MB_JAVA):
        text = path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_JDBC_CALLS:
            if token in text:
                bad.append(f"{path.relative_to(ROOT)}: {token}")
    assert not bad, "骨架误用 JdbcSupport API:\n" + "\n".join(bad)


def test_baseline_stores_use_jdbc_support_jdbc() -> None:
    """baseline 里凡调用 JdbcSupport.*，只能是 jdbc()。"""
    bad: list[str] = []
    for path in (BASE_JAVA / "com/thesis").rglob("*.java"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "JdbcSupport." not in line or line.strip().startswith("//") or line.strip().startswith("*"):
                continue
            if "JdbcSupport.jdbc()" in line:
                continue
            if "import " in line:
                continue
            bad.append(f"{path.relative_to(ROOT)}: {line.strip()}")
    assert not bad, "baseline 误用 JdbcSupport API:\n" + "\n".join(bad)


def test_no_void_require_admin_assigned_to_string() -> None:
    bad: list[str] = []
    for path in _java_files(BASE_JAVA):
        text = path.read_text(encoding="utf-8")
        if _FORBIDDEN_AUTH in text:
            bad.append(str(path.relative_to(ROOT)))
    assert not bad, "AdminAuth.requireAdmin 返回 void，不能赋给 String:\n" + "\n".join(bad)


def test_session_login_name_is_uid_not_username() -> None:
    """Auth 只写 session.uid；读 username 会得到 null→\"null\"，商家看板全 0。"""
    bad: list[str] = []
    for path in _java_files(BASE_JAVA):
        text = path.read_text(encoding="utf-8")
        if 'getAttribute("username")' in text or "getAttribute('username')" in text:
            bad.append(str(path.relative_to(ROOT)))
    assert not bad, "应用 AdminAuth.requireLogin / session.uid，禁止 getAttribute(\"username\"):\n" + "\n".join(bad)


def test_mybatis_overlay_has_no_spring_jdbc() -> None:
    bad: list[str] = []
    for path in _java_files(MB_JAVA):
        text = path.read_text(encoding="utf-8")
        if "import com.thesis.config.JdbcSupport" in text:
            bad.append(str(path.relative_to(ROOT)))
        elif "JdbcSupport.jdbc" in text and "对标原 JdbcSupport" not in text:
            bad.append(str(path.relative_to(ROOT)))
        if "import org.springframework.jdbc.core.JdbcTemplate" in text:
            bad.append(str(path.relative_to(ROOT)))
    assert not bad, "mybatis 叠层仍含 JDBC:\n" + "\n".join(bad)


def test_jpa_overlay_stores_use_jpa_support() -> None:
    for name in ("FrontDeskStore.java", "RoomBoardStore.java", "DigitalGoodsStore.java", "RentalBondStore.java"):
        path = JPA_JAVA / "com/thesis/capability" / name
        text = path.read_text(encoding="utf-8")
        assert "JpaSupport.db()" in text, name
        assert "JdbcSupport" not in text or "对标原 JdbcSupport" in text
        assert "import com.thesis.config.JdbcSupport" not in text


# baseline 后加的能力开关 API，mybatis/jpa 叠层必须同源，否则首次 bake 非 jdbc 栈编译失败
_OVERLAY_API_MARKERS = (
    ("capability/TicketStore.java", "configureRenew("),
    ("capability/TicketStore.java", "configureWaitlist("),
    ("capability/TicketStore.java", "configureBookHold("),
    ("capability/TicketStore.java", "hideForReport("),
    ("capability/TicketStore.java", "claimHold("),
    ("capability/TicketStore.java", " Map<String, Object> renew("),
    ("service/MessageStore.java", "configureTemplate("),
    ("service/MessageStore.java", "templateEnabled()"),
    ("service/MessageStore.java", "sendWithTemplate("),
    ("service/MessageStore.java", "pageTemplates("),
    ("service/MessageStore.java", "updateTemplate("),
    ("service/UserStore.java", "configurePostMute("),
    ("service/UserStore.java", "postMuteEnabled()"),
    ("service/UserStore.java", "setPostMuteUntil("),
    ("service/UserStore.java", "setPostMuteDays("),
    ("capability/TicketLookupStore.java", "unitCapacityLabel"),
)


def test_overlay_stores_share_baseline_capability_apis() -> None:
    missing: list[str] = []
    for root, label in ((MB_JAVA, "mybatis"), (JPA_JAVA, "jpa")):
        for rel, marker in _OVERLAY_API_MARKERS:
            path = root / "com/thesis" / rel
            text = path.read_text(encoding="utf-8")
            if marker not in text:
                missing.append(f"{label}:{rel}: {marker}")
    for root, label, db_name in (
        (MB_JAVA, "mybatis", "MbSql.java"),
        (JPA_JAVA, "jpa", "JpaDb.java"),
    ):
        text = (root / "com/thesis/config" / db_name).read_text(encoding="utf-8")
        if "queryForObject(String sql, SqlRowMapper" not in text:
            missing.append(f"{label}:{db_name}: queryForObject(SqlRowMapper)")
    assert not missing, "叠层 Store API 相对 baseline 漂移:\n" + "\n".join(missing)
