from pathlib import Path

# 1) core.armor_status: 判据与 patch 脚本一致（打补丁后 <content_policy> 仍在，但内容已换成 ARMOR_OFF）
c = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\wbarmor\core.py")
t = c.read_text(encoding="utf-8")
old = '''        has_canary = CANARY in text
        has_policy = "<content_policy>" in text
        state = "ARMOR-OFF" if (has_canary and not has_policy) else ("ORIGINAL" if has_policy else "NO-POLICY")'''
new = '''        has_canary = CANARY in text or "ARMOR_OFF" in text
        has_policy = "<content_policy>" in text
        # patch-armor 的语义：保留 <content_policy> 标签但把内容换成 ARMOR_OFF 中性块
        state = "ARMOR-OFF" if has_canary else ("ORIGINAL" if has_policy else "NO-POLICY")'''
assert old in t, "armor_status anchor missing"
t = t.replace(old, new, 1)
c.write_text(t, encoding="utf-8")
print("core armor_status patched")

# 2) cdp-token: 选页时跳过 about:blank，必要时自己开一个目标页
m = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\scripts\cdp-token.mjs")
s = m.read_text(encoding="utf-8")
old2 = """async function ensurePage() {
  const list = await json('/json/list').catch(() => []);
  const pages = (Array.isArray(list) ? list : []).filter((t) => t.type === 'page' && t.webSocketDebuggerUrl);
  const hit = pages.find((t) => /workbuddy|codebuddy/i.test(t.url)) || pages[0];
  if (hit) return hit;
  const target = process.env.CDP_URL || 'https://www.workbuddy.ai';
  const created = await json('/json/new?' + encodeURIComponent(target)).catch(() => null);
  if (created && created.webSocketDebuggerUrl) return created;
  throw new Error('no page target (open a browser window first)');
}"""
new2 = """async function openTarget(url) {
  for (const method of ['PUT', 'GET']) {
    try {
      const r = await fetch(BASE + '/json/new?' + encodeURIComponent(url), { method });
      if (r.ok) {
        const j = await r.json().catch(() => null);
        if (j && j.webSocketDebuggerUrl) return j;
      }
    } catch { }
  }
  return null;
}

async function ensurePage() {
  const list = await json('/json/list').catch(() => []);
  const pages = (Array.isArray(list) ? list : []).filter((t) => t.type === 'page' && t.webSocketDebuggerUrl);
  const real = pages.filter((t) => t.url && t.url !== 'about:blank');
  const hit = real.find((t) => /workbuddy|codebuddy|\\/login/i.test(t.url)) || real[0];
  if (hit) return hit;
  const target = process.env.CDP_URL || 'https://www.workbuddy.ai/login?platform=workbuddy-ai';
  const created = await openTarget(target);
  if (created) {
    await new Promise((r) => setTimeout(r, 1500));   // 等导航发起
    return created;
  }
  throw new Error('no usable page target (only about:blank); open the login tab first');
}"""
assert old2 in s, "ensurePage anchor missing"
s = s.replace(old2, new2, 1)
m.write_text(s, encoding="utf-8")
print("cdp-token ensurePage patched")
