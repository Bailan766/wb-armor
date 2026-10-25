// 从本地 Chrome/Edge 的 CDP 端口抓取 token（localStorage / sessionStorage）
// usage: node scripts/cdp-token.mjs [--port 9222] [--json]
const port = Number((process.argv.find((a) => a.startsWith('--port=')) || '').split('=')[1] || process.env.CDP_PORT || 9222);
const asJson = process.argv.includes('--json');
const BASE = `http://127.0.0.1:${port}`;

const TOKENISH = /(token|jwt|credential|session|auth)/i;
const JWTISH = /eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\./;

function pickToken(key, value) {
  if (!value || typeof value !== 'string') return false;
  if (TOKENISH.test(key)) return true;
  if (JWTISH.test(value)) return true;
  return false;
}

function classify(key) {
  const k = key.toLowerCase();
  if (k.includes('refresh')) return 'refresh';
  if (k.includes('device')) return 'device';
  if (k.includes('access') || k.includes('token') || k.includes('jwt')) return 'access';
  return 'other';
}

async function json(path) {
  const r = await fetch(BASE + path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return r.json();
}

async function openTarget(url) {
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
  const hit = real.find((t) => /workbuddy|codebuddy|\/login/i.test(t.url)) || real[0];
  if (hit) return hit;
  const target = process.env.CDP_URL || 'https://www.workbuddy.ai/login?platform=workbuddy-ai';
  const created = await openTarget(target);
  if (created) {
    await new Promise((r) => setTimeout(r, 1500));   // 等导航发起
    return created;
  }
  throw new Error('no usable page target (only about:blank); open the login tab first');
}

function cdp(ws, id, method, params = {}) {
  return new Promise((resolve, reject) => {
    const onMsg = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch { return; }
      if (m.id !== id) return;
      ws.removeEventListener('message', onMsg);
      if (m.error) reject(new Error(method + ': ' + m.error.message));
      else resolve(m.result);
    };
    ws.addEventListener('message', onMsg);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => reject(new Error(method + ' timeout')), 8000);
  });
}

const EXPR = `(() => {
  const out = [];
  const scan = (storeName, store) => {
    for (let i = 0; i < store.length; i++) {
      const k = store.key(i);
      const v = store.getItem(k);
      if (v && v.length < 8000) out.push({ storage: storeName, key: k, value: v });
    }
  };
  try { scan('local', window.localStorage); } catch (e) {}
  try { scan('session', window.sessionStorage); } catch (e) {}
  return JSON.stringify({ origin: location.origin, href: location.href, entries: out });
})()`;

const LANDING = '(function(){const g=(k)=>{try{return localStorage.getItem(k)}catch(e){return null}};' +
  'const s=(k)=>{try{return sessionStorage.getItem(k)}catch(e){return null}};' +
  'return {href:location.href,keys:[...Object.keys(localStorage),...Object.keys(sessionStorage)]};})()';

async function run() {
  const page = await ensurePage();
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true });
    ws.addEventListener('error', () => rej(new Error('ws error')), { once: true });
    setTimeout(() => rej(new Error('ws timeout')), 6000);
  });
  let id = 1;
  await cdp(ws, id++, 'Runtime.enable');
  const probe = await cdp(ws, id++, 'Runtime.evaluate', { expression: LANDING, returnByValue: true });
  const info = probe?.result?.value || {};
  const allowAny = process.env.CDP_ALLOW_ANY === '1' || process.argv.includes('--any');
  if (!allowAny && info && info.href && !/workbuddy|codebuddy|login|oauth/i.test(info.href)) {
    // 不在目标站点时不强行抓取，只报告
    ws.close();
    return { ok: false, reason: 'not on workbuddy/codebuddy page', href: info.href, keys: info.keys || [] };
  }
  const res = await cdp(ws, id++, 'Runtime.evaluate', { expression: EXPR, returnByValue: true });
  ws.close();
  let parsed = {};
  try { parsed = JSON.parse(res?.result?.value || '{}'); } catch { parsed = {}; }
  const usable = (parsed.entries || [])
    .filter((e) => !/^__|beacon|gtag|ga_|sentry/i.test(e.key))
    .filter((e) => pickToken(e.key, e.value))
    .map((e) => ({ kind: classify(e.key), storage: e.storage, key: e.key, value: e.value }))
    .filter((e) => e.kind !== 'other');
  const onLoginPage = /\/login|\/auth|signin|sso/i.test(parsed.href || '');
  const reason = usable.length ? null
    : (onLoginPage ? 'still on login page - finish login first' : 'no usable token in storage');
  return { ok: usable.length > 0, origin: parsed.origin, href: parsed.href,
           count: usable.length, tokens: usable, reason, login_page: onLoginPage };
}

try {
  const out = await run();
  if (asJson) console.log(JSON.stringify(out));
  else {
    if (!out.ok) console.log('CAPTURE fail: ' + (out.reason || 'no token in storage') + ' href=' + (out.href || '?'));
    else {
      console.log(`CAPTURE ok origin=${out.origin} tokens=${out.count}`);
      for (const t of out.tokens) {
        const v = t.value;
        console.log(`  [${t.kind}] ${t.storage}:${t.key} len=${v.length} head=${v.slice(0, 12)}…`);
      }
    }
  }
  process.exit(out.ok ? 0 : 1);
} catch (e) {
  console.error('CAPTURE error: ' + e.message);
  process.exit(2);
}
