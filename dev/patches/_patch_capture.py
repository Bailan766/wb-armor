from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\scripts\cdp-token.mjs")
t = p.read_text(encoding="utf-8")

t = t.replace(
    "  const tokens = (parsed.entries || [])\n    .filter((e) => pickToken(e.key, e.value))\n    .map((e) => ({ kind: classify(e.key), storage: e.storage, key: e.key, value: e.value }));\n  return { ok: tokens.length > 0, origin: parsed.origin, href: parsed.href, count: tokens.length, tokens };",
    "  const usable = (parsed.entries || [])\n"
    "    .filter((e) => !/^__|beacon|gtag|ga_|sentry/i.test(e.key))\n"
    "    .filter((e) => pickToken(e.key, e.value))\n"
    "    .map((e) => ({ kind: classify(e.key), storage: e.storage, key: e.key, value: e.value }))\n"
    "    .filter((e) => e.kind !== 'other');\n"
    "  const onLoginPage = /\\/login|\\/auth|signin|sso/i.test(parsed.href || '');\n"
    "  const reason = usable.length ? null\n"
    "    : (onLoginPage ? 'still on login page - finish login first' : 'no usable token in storage');\n"
    "  return { ok: usable.length > 0, origin: parsed.origin, href: parsed.href,\n"
    "           count: usable.length, tokens: usable, reason, login_page: onLoginPage };"
)

p.write_text(t, encoding="utf-8")

c = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
ct = c.read_text(encoding="utf-8")
ct = ct.replace(
    '            if not data.get("ok") and not data.get("reason"):\n'
    '                data["reason"] = "页面已连上，但 localStorage/sessionStorage 里没有 token（未登录？）"',
    '            if not data.get("ok") and not data.get("reason"):\n'
    '                data["reason"] = ("仍在登录页，先完成登录" if data.get("login_page")\n'
    '                                  else "页面已连上，但存储里没有可用的 access/device/refresh token")'
)
c.write_text(ct, encoding="utf-8")
print("patched cdp-token.mjs + core reason")
