from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

# 1) _dsh_yaml 加标记 + 参数
start = t.index("def _dsh_yaml(")
end = t.index("def _prune_dsh_bundles(")
new_yaml = '''def _dsh_yaml(armor: bool = True, insert: bool = False) -> str:
    """DSH patch 层必须是「顶层 YAML 数组 + id/config 条目」；写成 mapping 会直接报
    `must be a top-level YAML array of loader patch entries`，整个 profile 起不来。
    带 begin/end 标记，便于重复部署时只替换本块、保留用户其它条目。"""
    persona = ARMOR_OFF_TEXT if armor else "You are a helpful assistant."
    indent = "\\n".join("      " + ln for ln in persona.splitlines())
    head = "# >>> wb-armor overlay (managed block; safe to delete)\\n"
    if insert:
        head += "- insert:\\n    - id: dsh-infinite-gen-5\\n      name: 'dsh-infinite-gen-5'\\n\\n"
    return head + (
        "- id: agent-default-model\\n"
        "  config:\\n"
        "    provider: deepseek-official\\n"
        "    model: deepseek-v4.1-flash\\n"
        "\\n"
        "- id: llm-deepseek\\n"
        "  config:\\n"
        "    baseURL: http://127.0.0.1:8790/v1\\n"
        "    apiKey: sk-local-ig5\\n"
        "    models:\\n"
        "      - id: deepseek-v4.1-flash\\n"
        "        name: DeepSeek-V4.1-Flash (wb-armor bridge)\\n"
        "        contextWindow: 1000000\\n"
        "        inputModalities: [text]\\n"
        "\\n"
        "- id: system-prompt\\n"
        "  config:\\n"
        "    personaPrefix: |-\\n"
        + indent + "\\n"
        "      \\n"
        "      << armor canary: %s >>\\n" % CANARY
        + "# <<< wb-armor overlay\\n"
    )


'''
t = t[:start] + new_yaml + t[end:]

# 2) deploy_dsh 覆盖 web / desktop / tauri（存在即写），headless 可选；合并而非覆盖
dstart = t.index("def deploy_dsh(")
dend = t.index("# ---------------------------------------------------------------- services")
new_deploy = '''DSH_PROFILE_NAMES = ["web", "desktop", "tauri"]


def _strip_our_block(text: str) -> str:
    b = text.find("# >>> wb-armor overlay")
    e = text.find("# <<< wb-armor overlay")
    if b >= 0 and e > b:
        return (text[:b] + text[e + len("# <<< wb-armor overlay\\n"):]).rstrip() + "\\n"
    return text


def deploy_dsh(headless: bool = False, dry: bool = False) -> list[str]:
    out: list[str] = []
    names = list(DSH_PROFILE_NAMES) + (["headless"] if headless else [])
    for name in names:
        prof_dir = HOME / ".dsh" / "profiles" / name
        patch = prof_dir / "cordis.patch.yml"
        if not prof_dir.exists():
            continue
        if patch.exists():
            bak = patch.with_suffix(".yml.bak")
            bak.write_text(patch.read_text(encoding="utf-8"), encoding="utf-8")
            existing = patch.read_text(encoding="utf-8")
            out.append("backup %s/%s" % (name, bak.name))
        else:
            existing = "[]\\n"
            out.append("%s: new patch file" % name)
        insert_ok = (prof_dir / "node_modules" / "dsh-infinite-gen-5").exists()
        base = _strip_our_block(existing)
        if base.strip() in ("", "[]"):
            base = ""
        body = base + ("\\n" if base else "") + _dsh_yaml(armor=True, insert=insert_ok)
        if not dry:
            patch.write_text(body, encoding="utf-8")
            pruned = _prune_dsh_bundles(prof_dir)
            if pruned:
                out.append("%s: %s" % (name, pruned))
        out.append("%s %s (canary=%s, insert=%s)" % ("wrote" if not dry else "would write", patch, CANARY in body, insert_ok))
    if not dry:
        out.append(_ensure_dsh_key())
    out.append("verify: dsh --profile %s --help   (期望无 skipping/parse 报错)" % names[0])
    return out


'''
t = t[:dstart] + new_deploy + t[dend:]
p.write_text(t, encoding="utf-8")
print("deploy_dsh now targets:", "web/desktop/tauri(+headless)")
