from pathlib import Path

p = Path(r"C:\Users\Administrator\Desktop\wb 一键破甲反代\src\ig5-bridge.mjs")
t = p.read_text(encoding="utf-8")

old_stats = "const STATS = { served: 0, fallbacks: 0, lastModel: null, lastStatus: 0 };"
new_stats = "const STATS = { served: 0, fallbacks: 0, lastModel: null, lastStatus: 0, routes: { responses: 0, chat: 0, messages: 0 } };"
assert old_stats in t
t = t.replace(old_stats, new_stats, 1)

old_note = """const note = (req, code) => {
  LOG.push(`${new Date().toISOString()} ${req.method} ${req.url} -> ${code}`);
  if (LOG.length > 200) LOG.shift();
  if (req && String(req.url || '').includes('/responses')) STATS.lastStatus = code;
};"""
new_note = """const note = (req, code) => {
  const url = String((req && req.url) || '');
  LOG.push(`${new Date().toISOString()} ${req.method} ${url} -> ${code}`);
  if (LOG.length > 200) LOG.shift();
  const post = req && req.method === 'POST';
  if (post && url.includes('/responses')) { STATS.routes.responses += 1; STATS.lastStatus = code; }
  else if (post && url.includes('/chat/completions')) STATS.routes.chat += 1;
  else if (post && url.includes('/messages')) STATS.routes.messages += 1;
};"""
assert old_note in t
t = t.replace(old_note, new_note, 1)

# /health 增加分路由计数
old_served = "      served: STATS.served, fallbacks: STATS.fallbacks,"
new_served = "      served: STATS.served, fallbacks: STATS.fallbacks, served_by_route: STATS.routes,"
assert old_served in t
t = t.replace(old_served, new_served, 1)

p.write_text(t, encoding="utf-8")
print("bridge counters patched")
