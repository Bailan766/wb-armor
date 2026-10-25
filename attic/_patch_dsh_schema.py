from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = p.read_text(encoding="utf-8")

start = t.index("def _dsh_yaml(")
end = t.index("def deploy_dsh(")

new = '''def _dsh_yaml(armor: bool = True) -> str:
    """DSH 的 patch 层必须是「顶层 YAML 数组 + id/config 条目」；写成 mapping 会直接报
    `must be a top-level YAML array of loader patch entries` 而整个 profile 起不来。"""
    persona = ARMOR_OFF_TEXT if armor else "You are a helpful assistant."
    indent = "\\n".join("      " + ln for ln in persona.splitlines())
    return (
        "# wb-armor overlay: 顶层数组，元素为 loader patch 条目（id + config）\\n"
        "- insert:\\n"
        "    - id: dsh-infinite-gen-5\\n"
        "      name: 'dsh-infinite-gen-5'\\n"
        "\\n"
        "- id: agent-default-model\\n"
        "  config:\\n"
        "    provider: deepseek-official\\n"
        "    model: deepseek-v4.1-flash\\n"
        "\\n"
        "- id: llm-deepseek\\n"
        "  config:\\n"
        "    baseURL: http://127.0.0.1:8790/v1\\n"
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
    )


'''

t = t[:start] + new + t[end:]
p.write_text(t, encoding="utf-8")
print("deploy_dsh generator rewritten; bytes=", p.stat().st_size)
