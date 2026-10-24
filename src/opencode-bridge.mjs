// opencode 免费模型的 OpenAI 兼容外壳：8792 → 本地 opencode serve (4097)
import http from 'node:http';
import { createLogger } from '../lib/log.mjs';

const log = createLogger('oc');

const PORT = Number(process.env.OC_BRIDGE_PORT || 8792);
const SRV = process.env.OC_SERVE || 'http://127.0.0.1:4097';
const FREE = ['deepseek-v4.1-flash-free', 'glm-5.3-flash-free', 'mimo-v2.6-flash-free',
  'nemotron-3-ultra-free', 'nemotron-3.5-lightning-free', 'nemotron-3.5-super-vl-free',
  'flint-40b-free', 'beam-free', 'big-pickle'];
let sessionId = null;

const j = (res, code, o) => { const b = JSON.stringify(o); res.writeHead(code, { 'content-type': 'application/json', 'content-length': Buffer.byteLength(b) }); res.end(b); };
const body = async (req) => { const c = []; for await (const x of req) c.push(x); return Buffer.concat(c).toString('utf8'); };

async function ensureSession() {
  // 默认每次请求新建 session：复用单一 session 会把历史一路累积（实测一句“只回四个字”烧到 98k tokens）
  if (process.env.OC_REUSE === '1' && sessionId) return sessionId;
  const r = await fetch(SRV + '/session', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'oc-bridge' }) });
  if (!r.ok) throw new Error('session ' + r.status);
  const id = (await r.json()).id;
  if (process.env.OC_REUSE === '1') sessionId = id;
  return id;
}
// 去掉零宽字符（模型偶尔在首字符前塞 U+200B，客户端会显示成“\u200b好”）
const ZW = /[\u200b\u200c\u200d\ufeff\u2060]/g;

http.createServer(async (req, res) => {
  try {
    if (req.method === 'GET' && /\/v1\/models/.test(req.url)) {
      return j(res, 200, { object: 'list', data: FREE.map((id) => ({ id, object: 'model', owned_by: 'opencode-free' })) });
    }
    if (req.method === 'GET' && /\/health/.test(req.url)) {
      return j(res, 200, { ok: true, serve: SRV, session: sessionId, models: FREE.length });
    }
    if (req.method === 'POST' && /\/v1\/chat\/completions/.test(req.url)) {
      const rid = log.rid();
      const b = JSON.parse((await body(req)) || '{}');
      const model = String(b.model || 'deepseek-v4.1-flash-free').replace(/^opencode\//, '');
      const text = (Array.isArray(b.messages) ? b.messages : []).map((m) => (m.role === 'system' ? '[system] ' : '') + (typeof m.content === 'string' ? m.content : '')).join('\n');
      const payload = { model: { providerID: 'opencode', modelID: model }, parts: [{ type: 'text', text }] };
      // serve 的 message schema 只有 { model, parts, ... }，不接受额外 tools 字段（会报 BadRequest）。
      // 免费档模型本身是 agent，工具能力来自 serve 进程内部的工具集，不由请求体注入。
      const t0 = Date.now();
      log.info('chat.start', { rid, model, chars: text.length });
      let sid = await ensureSession();
      const call = async (id) => fetch(`${SRV}/session/${id}/message`, {
        method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload)
      });
      let r = await call(sid);
      // serve 重启后 session 会失效：404/400 时重建一次 session 再试，避免桥假死
      if (r.status === 404 || r.status === 400) {
        sid = null; sessionId = null; sid = await ensureSession(); r = await call(sid);
      }
      if (!r.ok) { const t = await r.text(); return j(res, r.status, { error: t.slice(0, 300) }); }
      const data = await r.json();
      log.info('chat.done', { rid, model, tokens: data.info && data.info.tokens && data.info.tokens.total, ms: Date.now() - t0 });
      const out = (data.parts || []).filter((p) => p.type === 'text').map((p) => p.text).join('').replace(ZW, '').trim();
      const toolParts = (data.parts || []).filter((p) => p.type === 'tool' || p.type === 'tool-call');
      const finish = toolParts.length ? 'tool_calls' : 'stop';
      const tool_calls = toolParts.map((p, i) => ({
        id: p.id || ('call_' + i), type: 'function',
        function: { name: (p.tool || p.name || 'tool'), arguments: JSON.stringify(p.input || p.args || {}) }
      }));
      return j(res, 200, {
        id: data.info && data.info.id, object: 'chat.completion', created: Math.floor(Date.now() / 1000), model,
        choices: [{ index: 0, message: Object.assign({ role: 'assistant', content: out }, tool_calls.length ? { tool_calls } : {}), finish_reason: finish }],
        usage: {
          prompt_tokens: (data.info && data.info.tokens && data.info.tokens.input) || 0,
          completion_tokens: (data.info && data.info.tokens && data.info.tokens.output) || 0,
          total_tokens: (data.info && data.info.tokens && data.info.tokens.total) || 0
        }
      });
    }
    j(res, 404, { error: 'not found' });
  } catch (e) {
    log.error('handler.error', { msg: String((e && e.message) || e) });
    j(res, 500, { error: String((e && e.message) || e) });
  }
}).listen(PORT, '127.0.0.1', () => console.log('opencode-bridge on ' + PORT + ' -> ' + SRV));
