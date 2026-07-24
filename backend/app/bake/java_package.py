"""学生端 Java 包名：按领域区分，避免交付物全是 com.thesis。"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

# domain → (java package, Application 类名, Maven artifactId)
_DOMAIN_JAVA: dict[str, tuple[str, str, str]] = {
    "DOM-LIBRARY": ("com.campus.library", "LibraryApplication", "library-app"),
    "DOM-EQUIP": ("com.campus.equipment", "EquipmentApplication", "equipment-app"),
    "DOM-ASSET": ("com.campus.asset", "AssetApplication", "asset-app"),
    "DOM-CRM": ("com.campus.crm", "CrmApplication", "crm-app"),
    "DOM-EVENT": ("com.campus.event", "EventApplication", "event-app"),
    "DOM-ATTEND": ("com.campus.attend", "AttendApplication", "attend-app"),
    "DOM-FUND": ("com.campus.fund", "FundApplication", "fund-app"),
    "DOM-LABSAFE": ("com.campus.labsafe", "LabsafeApplication", "labsafe-app"),
    "DOM-RECRUIT": ("com.campus.recruit", "RecruitApplication", "recruit-app"),
    "DOM-GRADE": ("com.campus.grade", "GradeApplication", "grade-app"),
    "DOM-INTERN": ("com.campus.intern", "InternApplication", "intern-app"),
    "DOM-PARCEL": ("com.campus.parcel", "ParcelApplication", "parcel-app"),
    "DOM-DORM": ("com.campus.dorm", "DormApplication", "dorm-app"),
    "DOM-PROPERTY": ("com.campus.property", "PropertyApplication", "property-app"),
    "DOM-IT": ("com.campus.ithelp", "ItHelpApplication", "ithelp-app"),
    "DOM-ACTIVITY": ("com.campus.activity", "ActivityApplication", "activity-app"),
    "DOM-LOST": ("com.campus.lostfound", "LostFoundApplication", "lostfound-app"),
    "DOM-COURSE": ("com.campus.course", "CourseApplication", "course-app"),
    "DOM-SHOP": ("com.campus.shop", "ShopApplication", "shop-app"),
    "DOM-FOOD": ("com.campus.food", "FoodApplication", "food-app"),
    "DOM-HOSPITAL": ("com.campus.hospital", "HospitalApplication", "hospital-app"),
    "DOM-PARKING": ("com.campus.parking", "ParkingApplication", "parking-app"),
    "DOM-MEETING": ("com.campus.meeting", "MeetingApplication", "meeting-app"),
    "DOM-SALON": ("com.campus.salon", "SalonApplication", "salon-app"),
    "DOM-HOTEL": ("com.campus.hotel", "HotelApplication", "hotel-app"),
    "DOM-MEDIA": ("com.campus.media", "MediaApplication", "media-app"),
    "DOM-MUSIC": ("com.campus.music", "MusicApplication", "music-app"),
    "DOM-FORUM": ("com.campus.forum", "ForumApplication", "forum-app"),
    "DOM-BLOG": ("com.campus.blog", "BlogApplication", "blog-app"),
    "DOM-GENERIC": ("com.campus.app", "AppApplication", "campus-app"),
}

_OLD_PKG = "com.thesis"
_OLD_APP = "ThesisApplication"


def java_coords_for_domain(domain: str) -> tuple[str, str, str]:
    """返回 (package, ApplicationClass, artifactId)。"""
    return _DOMAIN_JAVA.get(domain) or _DOMAIN_JAVA["DOM-GENERIC"]


def java_coords_for_delivery(
    domain: str, slug: str | None = None, project_id: str = ""
) -> tuple[str, str, str]:
    """题目语义 → 包坐标（像普通毕设）；project_id 仅兼容调用方，不进包名。"""
    from app.bake.naming import java_coords_from_slug, sanitize_delivery_slug

    _ = project_id
    s = sanitize_delivery_slug((slug or "").strip() or None, domain=domain)
    domain_only = sanitize_delivery_slug(None, domain=domain)
    use_catalog = not (slug or "").strip() or s == domain_only

    if use_catalog:
        return java_coords_for_domain(domain)

    return java_coords_from_slug(s)


def find_java_package_root(workspace: Path) -> Path:
    """含 controller/ 的包根目录（…/java/com/campus/library）。"""
    java = workspace / "backend" / "src" / "main" / "java"
    if not java.is_dir():
        return java / "com" / "thesis"
    controllers = sorted(p for p in java.rglob("controller") if p.is_dir())
    if controllers:
        return controllers[0].parent
    # 兜底：任意 *Application.java 所在目录
    apps = sorted(java.rglob("*Application.java"))
    if apps:
        return apps[0].parent
    return java / "com" / "thesis"


def rewrite_gate_file_paths(files: list[str], new_package: str) -> list[str]:
    """把契约里的 com/thesis 路径改成新包路径。"""
    old_slash = _OLD_PKG.replace(".", "/")
    new_slash = new_package.replace(".", "/")
    out: list[str] = []
    for f in files:
        s = str(f).replace("\\", "/")
        if f"/{old_slash}/" in f"/{s}" or s.endswith(f"/{old_slash}") or f"/{old_slash}/" in s:
            s = s.replace(old_slash, new_slash)
        out.append(s)
    return out


def remap_student_java_package(
    workspace: Path,
    domain: str,
    slug: str | None = None,
    project_id: str = "",
) -> str:
    """将骨架 com.thesis 重映射为领域/题目包名；返回新 package。"""
    new_pkg, app_class, artifact = java_coords_for_delivery(domain, slug, project_id)
    if new_pkg == _OLD_PKG:
        return new_pkg

    java_root = workspace / "backend" / "src" / "main" / "java"
    old_dir = java_root.joinpath(*_OLD_PKG.split("."))
    if not old_dir.is_dir():
        # 可能已是别的包：仍清残留 target，并补写 mainClass
        pkg = find_java_package_root(workspace).relative_to(java_root).as_posix().replace("/", ".")
        apps = sorted((java_root / pkg.replace(".", "/")).glob("*Application.java"))
        if apps:
            app_class = apps[0].stem
            pom = workspace / "backend" / "pom.xml"
            if pom.is_file():
                pom.write_text(
                    _ensure_spring_boot_main_class(pom.read_text(encoding="utf-8"), f"{pkg}.{app_class}"),
                    encoding="utf-8",
                )
        purge_stale_thesis_classes(workspace / "backend")
        return pkg

    # 1) 改源码内容（仍在旧目录）
    for path in old_dir.rglob("*.java"):
        text = path.read_text(encoding="utf-8")
        text = text.replace(f"package {_OLD_PKG}.", f"package {new_pkg}.")
        text = text.replace(f"package {_OLD_PKG};", f"package {new_pkg};")
        text = text.replace(f"import {_OLD_PKG}.", f"import {new_pkg}.")
        text = text.replace(f"import {_OLD_PKG};", f"import {new_pkg};")
        if path.name == f"{_OLD_APP}.java":
            text = text.replace(_OLD_APP, app_class)
        path.write_text(text, encoding="utf-8")

    # 2) 挪目录
    new_dir = java_root.joinpath(*new_pkg.split("."))
    if new_dir.exists():
        shutil.rmtree(new_dir)
    new_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_dir), str(new_dir))

    # 清理空的 com/thesis 祖先
    for orphan in (java_root / "com" / "thesis", java_root / "com"):
        if orphan.is_dir() and not any(orphan.rglob("*")):
            try:
                orphan.rmdir()
            except OSError:
                pass

    # 3) 启动类文件名
    old_app = new_dir / f"{_OLD_APP}.java"
    new_app = new_dir / f"{app_class}.java"
    if old_app.is_file() and old_app != new_app:
        old_app.rename(new_app)

    # 4) pom.xml（含显式 mainClass，避免 target 残留双启动类）
    pom = workspace / "backend" / "pom.xml"
    if pom.is_file():
        pom_text = pom.read_text(encoding="utf-8")
        pom_text = re.sub(
            r"<groupId>com\.thesis</groupId>",
            f"<groupId>{new_pkg}</groupId>",
            pom_text,
            count=1,
        )
        pom_text = re.sub(
            r"<artifactId>thesis-app</artifactId>",
            f"<artifactId>{artifact}</artifactId>",
            pom_text,
            count=1,
        )
        pom_text = re.sub(
            r"<name>thesis-app</name>",
            f"<name>{artifact}</name>",
            pom_text,
            count=1,
        )
        pom_text = _ensure_spring_boot_main_class(pom_text, f"{new_pkg}.{app_class}")
        pom.write_text(pom_text, encoding="utf-8")

    # 5) application.yml spring.application.name
    yml = workspace / "backend" / "src" / "main" / "resources" / "application.yml"
    if yml.is_file():
        yml_text = yml.read_text(encoding="utf-8")
        yml_text = re.sub(
            r"(?m)^(\s*name:\s*)thesis-app\s*$",
            rf"\g<1>{artifact}",
            yml_text,
            count=1,
        )
        yml.write_text(yml_text, encoding="utf-8")

    # 6) 学生 README 包路径
    readme = workspace / "README.md"
    if readme.is_file():
        rd = readme.read_text(encoding="utf-8")
        rd = rd.replace("com/thesis/", new_pkg.replace(".", "/") + "/")
        rd = rd.replace("com.thesis", new_pkg)
        rd = rd.replace(_OLD_APP, app_class)
        readme.write_text(rd, encoding="utf-8")

    # 7) 清掉旧编译产物，否则 spring-boot:run 会扫到 ThesisApplication + 新启动类
    _purge_backend_target(workspace / "backend")

    return new_pkg


def _ensure_spring_boot_main_class(pom_text: str, main_class: str) -> str:
    """在 spring-boot-maven-plugin 上写入 / 覆盖 mainClass。"""
    plugin_pat = re.compile(
        r"(<plugin>\s*<groupId>org\.springframework\.boot</groupId>\s*"
        r"<artifactId>spring-boot-maven-plugin</artifactId>)(.*?)(</plugin>)",
        re.DOTALL,
    )
    m = plugin_pat.search(pom_text)
    if not m:
        return pom_text
    body = m.group(2)
    if re.search(r"<mainClass>.*?</mainClass>", body):
        body = re.sub(r"<mainClass>.*?</mainClass>", f"<mainClass>{main_class}</mainClass>", body, count=1)
    elif re.search(r"<configuration\b", body):
        body = re.sub(
            r"(<configuration[^>]*>)",
            rf"\1\n        <mainClass>{main_class}</mainClass>",
            body,
            count=1,
        )
    else:
        body = f"\n      <configuration>\n        <mainClass>{main_class}</mainClass>\n      </configuration>\n    "
    return pom_text[: m.start()] + m.group(1) + body + m.group(3) + pom_text[m.end() :]


def _purge_backend_target(backend: Path) -> None:
    target = backend / "target"
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)


def purge_stale_thesis_classes(backend: Path) -> None:
    """启动前：若源码已不在 com.thesis，清掉 target 里残留的旧启动类。"""
    java = backend / "src" / "main" / "java"
    old_src = java.joinpath(*_OLD_PKG.split("."))
    if old_src.is_dir():
        return
    stale = backend / "target" / "classes" / "com" / "thesis"
    if stale.exists():
        shutil.rmtree(stale, ignore_errors=True)
    # 若仍有多个 *Application.class，整目录清掉让 Maven 重编
    apps = list((backend / "target" / "classes").rglob("*Application.class")) if (backend / "target" / "classes").is_dir() else []
    if len(apps) > 1:
        _purge_backend_target(backend)
