"""dev/clean_profiles.py —— 一次性清理 ~/.dsh/profiles 里被叠加/写坏的 patch 层。

规则：每个 profile 先剥掉全部 wb-armor block（新旧标记都算），再按需追加**恰好一份**；
本来没有本工具 block 的 profile 不动。文件先备份成 .bak-YYYYmmddHHMM。
"""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wbarmor import core  # noqa: E402

PROFILES = ["web", "desktop", "tauri", "headless"]
stamp = time.strftime("%Y%m%d%H%M")


def strip_all(text: str) -> str:
    b = text.find("# wb-armor overlay:")
    if b >= 0:
        nxt = text.find("# >>> wb-armor overlay", b + 1)
        text = text[:b] + (text[nxt:] if nxt > b else "")
    while True:
        b = text.find("# >>> wb-armor overlay")
        e = text.find("# <<< wb-armor overlay", b) if b >= 0 else -1
        if b < 0 or e < 0:
            break
        text = text[:b] + text[e + len("# <<< wb-armor overlay"):]
    lines = [ln for ln in text.splitlines() if ln.strip() != "[]"]
    return "\n".join(lines).strip()


for name in PROFILES:
    prof = Path.home() / ".dsh" / "profiles" / name
    patch = prof / "cordis.patch.yml"
    if not patch.exists():
        print("%-9s skip (no patch)" % name)
        continue
    src = patch.read_text(encoding="utf-8")
    had_block = ("# >>> wb-armor overlay" in src) or ("# wb-armor overlay:" in src)
    base = strip_all(src)
    insert_ok = (prof / "node_modules" / "dsh-infinite-gen-5").exists()
    body = (base + "\n\n" if base else "") + (core._dsh_yaml(armor=True, insert=insert_ok) if had_block else "")
    bak = patch.with_name("cordis.patch.yml.bak-" + stamp)
    shutil.copy2(patch, bak)
    patch.write_text(body, encoding="utf-8")
    print("%-9s had_block=%-5s base_len=%-3d insert=%s -> %d bytes (bak %s)"
          % (name, had_block, len(base), insert_ok, len(body.encode("utf-8")), bak.name))
