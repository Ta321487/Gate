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
    # 房源成交台账：三套必须同源
    ("service/ListingDealStore.java", "public static String total()"),
    ("service/ListingDealStore.java", "BigDecimal dealPrice, String dealAt"),
    # 资助公示/发放旁路岛：三套必须同源
    ("service/FundPublicityStore.java", "listMine("),
    ("service/FundPublicityStore.java", "close(long id, String operator)"),
    ("service/FundDisburseStore.java", "totalOf("),
    ("service/FundDisburseStore.java", "BigDecimal amount, String paidAt"),
    # 举报处置一键禁言：叠层 FavoriteStore 必须与 baseline 同源（举报窗口多 muteDays 形参）
    ("capability/FavoriteStore.java", "takedown_mute"),
    ("capability/FavoriteStore.java", "int muteDays)"),
    # 单据可选列：周报周次（申请/补丁写库；胖工作流已抽到 TicketPatchOps）
    ("capability/TicketPatchOps.java", "\"weekNo\""),
    # 站内私信店铺客服可见性（买家↔商家），三套必须同源
    ("service/DmStore.java", "configureShopCustomerService("),
    ("service/DmStore.java", "shopCustomerService()"),
    ("service/DmStore.java", "canMessage("),
    # 教务成绩：改分留痕 / 分布统计 / CSV 导入（三套必须同源）
    ("service/GradeScoreStore.java", "importRows("),
    ("service/GradeScoreStore.java", "history(long scoreId)"),
    ("service/GradeScoreStore.java", "stats(Long courseId, Long termId)"),
    ("service/GradeScoreStore.java", "String operator)"),
)


def test_ticket_ops_no_false_ticketstore_prefix() -> None:
    """Ticket*Ops 拆分后禁止把局部变量/字面量误写成 TicketStore.xxx（会导致 javac 失败）。"""
    import re

    # 声明局部变量写成「类型 TicketStore.字段」
    decl = re.compile(r"\b(?:String|Long|Integer|int|boolean|double|float|var)\s+TicketStore\.[A-Za-z_]\w*")
    # SQL/Map/JSON 字面量里误带 TicketStore. 前缀（合法字段访问不含引号）
    quoted = re.compile(r"""['"]TicketStore\.[A-Za-z_][\w.]*['"]""")
    bad: list[str] = []
    for root in (BASE_JAVA, JPA_JAVA, MB_JAVA):
        for path in root.rglob("Ticket*Ops.java"):
            text = path.read_text(encoding="utf-8")
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith("//") or s.startswith("*"):
                    continue
                if decl.search(line) or quoted.search(line):
                    bad.append(f"{path.relative_to(ROOT)}:{i}: {s}")
    assert not bad, "Ticket*Ops 误带 TicketStore. 前缀:\n" + "\n".join(bad)


def test_ticket_store_delegates_fat_workflows_to_ops() -> None:
    """三栈 TicketStore 胖工作流须委托 *Ops，禁止再内联完整 complete/dashboard 正文。"""
    markers = (
        ("complete(", "TicketCompleteOps.complete("),
        ("dashboard(", "TicketDashOps.dashboard("),
        ("chartStats(", "TicketDashOps.chartStats("),
    )
    missing: list[str] = []
    for root, label in ((BASE_JAVA, "baseline"), (JPA_JAVA, "jpa"), (MB_JAVA, "mybatis")):
        path = root / "com/thesis/capability/TicketStore.java"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for _meth, needle in markers:
            if needle not in text:
                missing.append(f"{label}: missing {needle}")
    assert not missing, "TicketStore 未委托 Ops:\n" + "\n".join(missing)


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
