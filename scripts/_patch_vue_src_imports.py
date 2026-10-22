"""把读已拆分 Vue 的测试改为 vue_src 合读。"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend" / "tests"


def ensure_import(text: str) -> str:
    if "from tests._vue_src import vue_src" in text:
        return text
    needle = "from __future__ import annotations\n"
    if needle in text:
        return text.replace(
            needle,
            needle + "\nfrom tests._vue_src import vue_src\n",
            1,
        )
    return "from tests._vue_src import vue_src\n" + text


def patch_file(name: str, replacements: list[tuple[str, str]]) -> None:
    p = ROOT / name
    t = ensure_import(p.read_text(encoding="utf-8"))
    for old, new in replacements:
        if old not in t:
            print(f"WARN {name}: missing pattern:\n  {old[:80]!r}")
            continue
        t = t.replace(old, new)
    p.write_text(t, encoding="utf-8", newline="\n")
    print(f"OK {name}")


def main() -> None:
    simple = [
        ("MY.read_text(encoding=\"utf-8\")", "vue_src(MY)"),
        ("_MY_TICKETS.read_text(encoding=\"utf-8\")", "vue_src(_MY_TICKETS)"),
    ]
    for name in (
        "test_repair_look_polish.py",
        "test_approve_look_polish.py",
        "test_repair_look_thicken.py",
        "test_approve_look_thicken.py",
        "test_form_first_residual.py",
    ):
        patch_file(name, simple)

    patch_file(
        "test_interact_thicken_features.py",
        [
            (
                '(FE / "views" / "user" / "MyTickets.vue").read_text(encoding="utf-8")',
                'vue_src(FE / "views" / "user" / "MyTickets.vue")',
            ),
        ],
    )
    patch_file(
        "test_follow_gaps_delivery.py",
        [
            (
                '(FE / "user" / "MyTickets.vue").read_text(encoding="utf-8")',
                'vue_src(FE / "user" / "MyTickets.vue")',
            ),
        ],
    )
    for name in (
        "test_waitlist_e02.py",
        "test_loan_renew_e01.py",
        "test_code_qr_e07.py",
    ):
        patch_file(
            name,
            [
                (
                    '(BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(encoding="utf-8")',
                    'vue_src(BASELINE / "frontend/src/views/user/MyTickets.vue")',
                ),
            ],
        )

    # book_hold may be multiline
    p = ROOT / "test_book_hold_e11.py"
    t = ensure_import(p.read_text(encoding="utf-8"))
    t2 = t.replace(
        '(BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(\n'
        '            encoding="utf-8"\n'
        "        )",
        'vue_src(BASELINE / "frontend/src/views/user/MyTickets.vue")',
    )
    if t2 == t:
        t2 = t.replace(
            '(BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(encoding="utf-8")',
            'vue_src(BASELINE / "frontend/src/views/user/MyTickets.vue")',
        )
    p.write_text(t2, encoding="utf-8", newline="\n")
    print("OK test_book_hold_e11.py")

    patch_file(
        "test_opening_map_skeleton_gate.py",
        [
            (
                '_read(FE_SRC / "views" / "user" / "MyTickets.vue")',
                'vue_src(FE_SRC / "views" / "user" / "MyTickets.vue")',
            ),
        ],
    )

    patch_file(
        "test_multi_approve_c16.py",
        [
            (
                'self.assertIn("pending_mid", my.read_text(encoding="utf-8"))',
                'self.assertIn("pending_mid", vue_src(my))',
            ),
        ],
    )
    patch_file(
        "test_code_qr_e07.py",
        [
            (
                "text = my.read_text(encoding=\"utf-8\")",
                "text = vue_src(my)",
            ),
            (
                '(BASELINE / "frontend/src/views/user/MyTickets.vue").read_text(encoding="utf-8")',
                'vue_src(BASELINE / "frontend/src/views/user/MyTickets.vue")',
            ),
        ],
    )

    # opening_map: _read 对 .vue 走合读
    p = ROOT / "test_opening_map_skeleton_gate.py"
    t = ensure_import(p.read_text(encoding="utf-8"))
    t = t.replace(
        "def _read(p: Path) -> str:\n    return p.read_text(encoding=\"utf-8\")\n",
        "def _read(p: Path) -> str:\n"
        "    if p.suffix == \".vue\":\n"
        "        return vue_src(p)\n"
        "    return p.read_text(encoding=\"utf-8\")\n",
    )
    p.write_text(t, encoding="utf-8", newline="\n")
    print("OK test_opening_map_skeleton_gate.py _read")

    # sequence: copy companion files
    p = ROOT / "test_sequence_thicken_buttons.py"
    t = p.read_text(encoding="utf-8")
    if "stem}.setup.js" not in t:
        old = """        for rel in (
            "views/admin/TicketsAdmin.vue",
            "views/admin/TicketRecordsAdmin.vue",
            "views/user/MyFavorites.vue",
            "views/user/MyTickets.vue",
        ):
            dest = td / "frontend" / "src" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SK_FE / rel, dest)
"""
        new = """        for rel in (
            "views/admin/TicketsAdmin.vue",
            "views/admin/TicketRecordsAdmin.vue",
            "views/user/MyFavorites.vue",
            "views/user/MyTickets.vue",
        ):
            dest = td / "frontend" / "src" / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SK_FE / rel, dest)
            stem = Path(rel).stem
            parent = (SK_FE / rel).parent
            for ext in (f"{stem}.setup.js", f"{stem}.css"):
                side = parent / ext
                if side.is_file():
                    shutil.copy2(side, dest.parent / ext)
"""
        if old in t:
            p.write_text(t.replace(old, new), encoding="utf-8", newline="\n")
            print("OK test_sequence_thicken_buttons.py companions")
        else:
            print("WARN sequence block not found")

    # surface_lexicon: MY_TICKETS.read_text -> vue_src
    p = ROOT / "test_surface_lexicon.py"
    t = ensure_import(p.read_text(encoding="utf-8"))
    t = t.replace("MY_TICKETS.read_text(encoding=\"utf-8\")", "vue_src(MY_TICKETS)")
    p.write_text(t, encoding="utf-8", newline="\n")
    print("OK test_surface_lexicon.py")


if __name__ == "__main__":
    main()

