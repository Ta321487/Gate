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


def remap_student_java_package(workspace: Path, domain: str) -> str:
    """将骨架 com.thesis 重映射为领域包名；返回新 package。"""
    new_pkg, app_class, artifact = java_coords_for_domain(domain)
    if new_pkg == _OLD_PKG:
        return new_pkg

    java_root = workspace / "backend" / "src" / "main" / "java"
    old_dir = java_root.joinpath(*_OLD_PKG.split("."))
    if not old_dir.is_dir():
        # 可能已是别的包
        return find_java_package_root(workspace).relative_to(java_root).as_posix().replace("/", ".")

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

    # 4) pom.xml
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

    return new_pkg
