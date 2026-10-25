from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

old = '''def payload_info() -> dict:
    sel = ROOT / ".payload"
    current = ""
    if sel.exists():
        current = sel.read_text(encoding="utf-8", errors="replace").strip().lstrip("\\ufeff").strip()
    default = ROOT / "vendor" / "dsh-infinite-gen-5" / "infinite-gen-5.1-flash.md"
    active = current if (current and Path(current).exists()) else (str(default) if default.exists() else "")
    size = Path(active).stat().st_size if active and Path(active).exists() else 0
    return {"selector": str(sel), "selected": current, "active": active, "bytes": size, "default": str(default)}'''

new = '''BUNDLED_PAYLOAD = ROOT / "vendor" / "dsh-infinite-gen-5" / "infinite-gen-5.1-flash.md"


def payload_info() -> dict:
    """解析顺序：.payload 选择器 > 内置 vendor 副本；source=bundled 表示不依赖外部文件。"""
    sel = ROOT / ".payload"
    current = ""
    if sel.exists():
        current = sel.read_text(encoding="utf-8", errors="replace").strip().lstrip("\\ufeff").strip()
    if current and Path(current).exists():
        active, source = current, "selector"
    else:
        active = str(BUNDLED_PAYLOAD) if BUNDLED_PAYLOAD.exists() else ""
        source = "bundled"
    size = Path(active).stat().st_size if active and Path(active).exists() else 0
    return {"selector": str(sel), "selected": current, "active": active, "source": source,
            "bytes": size, "bundled": str(BUNDLED_PAYLOAD)}


def reset_payload() -> tuple[bool, str]:
    """.payload 删掉 -> 桥回落到内置 vendor 载荷。"""
    sel = ROOT / ".payload"
    if sel.exists():
        sel.unlink()
        return True, "已清除 .payload，桥将使用内置载荷 %s" % BUNDLED_PAYLOAD
    return True, "本来就在用内置载荷 %s" % BUNDLED_PAYLOAD'''

assert old in t, "payload_info anchor still missing"
t = t.replace(old, new, 1)
p.write_text(t, encoding="utf-8")
print("core patched; bytes=", p.stat().st_size)
