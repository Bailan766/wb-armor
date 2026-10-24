// IG5 桥 v12：上游流式可用时原样透传，退化时自合成事件流；失败兜底 opencode 免费档
import http from 'node:http';
import fs from 'node:fs';

const PORT = Number(process.env.IG5_PORT || 8790);
const UP = process.env.IG5_UPSTREAM || 'http://127.0.0.1:8788/v1';
const HERE = new URL('.', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const VENDOR = HERE + '../vendor/dsh-infinite-gen-5/infinite-gen-5.1-flash.md';
const DEFAULT_PAYLOAD = 'C:/Users/Administrator/Desktop/dsh-infinite-gen-5-main/prompts/infinite-gen-5.1-flash.md';
function resolvePayload() {
  for (const p of [process.env.IG5_PAYLOAD, DEFAULT_PAYLOAD, VENDOR]) {
    if (p && fs.existsSync(p)) return p;
  }
  throw new Error('no payload found (IG5_PAYLOAD / default / vendor)');
}
const PAYLOAD_PATH = resolvePayload();
const PAYLOAD = fs.readFileSync(PAYLOAD_PATH, 'utf8');
const LOG = [];
const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,OPTIONS', 'access-control-max-age': '86400' };
const DBG = () => process.env.IG5_DEBUG;
const dbg = (s) => { if (DBG()) fs.appendFileSync(HERE + 'ig5-debug.log', s); };
const note = (req, code) => { LOG.push(`${new Date().toISOString()} ${req.method} ${req.url} -> ${code}`); if (LOG.length > 200) LOG.shift(); };
const json = (res, code, obj, req) => { const b = JSON.stringify(obj); res.writeHead(code, { ...CORS, 'content-type': 'application/json', 'content-length': Buffer.byteLength(b) }); res.end(b); if (req) note(req, code); };
const readBody = async (req) => { const c = []; for await (const x of req) c.push(x); return Buffer.concat(c).toString('utf8'); };

// 把 Responses 的 input 转成 chat messages
const toText = (it) => (typeof it.content === 'string' ? it.content : (Array.isArray(it.content) ? it.content.map((c) => c.text || '').join('') : (it.text || '')));
function convoOf(body, keep = 8) {
  const items = Array.isArray(body.input) ? body.input : [];
  return items.slice(-keep).map((it) => ({
    role: it.role === 'assistant' ? 'assistant' : (it.role === 'system' || it.role === 'developer' ? 'system' : 'user'),
    content: toText(it)
  })).filter((m) => m.content);
}
async function askOpencode(model, messages) {
  const url = process.env.OC_BRIDGE || 'http://127.0.0.1:8792/v1/chat/completions';
  const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model, messages }) });
  const j = await r.json();
  const t = j && j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content;
  return r.ok && t ? t : '';
}

const server = http.createServer(async (req, res) => {
  try {
    if (req.method === 'OPTIONS') { res.writeHead(204, CORS); res.end(); return note(req, 204); }
    let p = (req.url || '/').split('?')[0].replace(/\/+$/, '') || '/';
    while (/^\/v1\/v1(\/|$)/.test(p)) p = p.replace(/^\/v1/, '');

    if (req.method === 'GET' && p === '/health') return json(res, 200, { ok: true, upstream: UP, payload_chars: PAYLOAD.length, recent: LOG.slice(-10) }, req);

    if (req.method === 'GET' && /\/models$/.test(p)) {
      const raw = await (await fetch(UP + '/models')).json();
      const list = Array.isArray(raw.data) ? raw.data : [];
      const clean = [];
      for (const m of list) {
        const id = String(m.id || '').replace(/\s*\(x[0-9.]+\)\s*$/i, '').trim();
        if (id) clean.push({ id, object: 'model', created: m.created || 0, owned_by: 'workbuddy-proxy', name: String(m.name || id).replace(/\s*\(x[0-9.]+\)\s*$/i, '').trim() });
      }
      clean.sort((a, b) => (a.id === 'deepseek-v4.1-flash' ? -1 : b.id === 'deepseek-v4.1-flash' ? 1 : 0));
      return json(res, 200, { object: 'list', data: clean, models: clean }, req);
    }

    if (req.method === 'POST' && /\/responses$/.test(p)) {
      const raw = (await readBody(req)) || '{}';
      const body = JSON.parse(raw);
      dbg(`\n=== ${new Date().toISOString()} REQ ===\n${raw.slice(0, 4000)}\n`);
      body.model = body.model || 'deepseek-v4.1-flash';
      const ocDirect = typeof body.model === 'string' && body.model.startsWith('oc-');
      if (ocDirect) body.model = body.model.slice(3);

      const instr = typeof body.instructions === 'string' ? body.instructions : '';
      delete body.instructions;
      const sysItem = { type: 'message', role: 'user', content: [{ type: 'input_text', text: PAYLOAD + (instr ? '\n\n' + instr : '') }] };
      const clean = (arr) => arr.map((it) => { const o = { ...it }; delete o.id; if (o.role === 'developer') o.role = 'system'; return o; });
      if (Array.isArray(body.input)) body.input = [sysItem, ...clean(body.input)];
      else body.input = [sysItem, { type: 'message', role: 'user', content: [{ type: 'input_text', text: String(body.input || '') }] }];

      if (Array.isArray(body.tools)) {
        const before = body.tools.length;
        const typesSeen = [...new Set(body.tools.map((t) => (t && (t.type || '?')) || '?'))].join(',');
        // 上游只认 {type:function,name,parameters}；其它类型（custom / namespace / web_search 等）
        // 包成 function 形态后【保留】，绝不丢弃 —— 丢弃 = 客户端工具（写文件 / patch / shell）凭空消失。
        // 归一化：name 缺失时回退 t.function.name 或 t.id；parameters 缺失给空 object（勿塞假 required）。
        const norm = (t) => {
          if (!t) return null;
          const fnObj = t.function && typeof t.function === 'object' ? t.function : null;
          const name = t.name || (fnObj && fnObj.name) || t.id || null;
          if (!name) return null;
          const desc = t.description || (fnObj && fnObj.description) || '';
          let params = t.parameters || (fnObj && fnObj.parameters) || null;
          if (!params || typeof params !== 'object') params = { type: 'object', properties: {} };
          if (params.type !== 'object' && !params.properties) params = { type: 'object', properties: {}, ...params };
          const o = { type: 'function', name, description: desc, parameters: params };
          if (t.strict !== undefined) o.strict = t.strict;
          return o;
        };
        const kept = []; const dropped = [];
        for (const t of body.tools) {
          const o = norm(t);
          if (o) kept.push(o); else dropped.push((t && (t.type || '?') + ':' + (t.name || t.id || '-')) || 'null');
        }
        body.tools = kept;
        // 丢掉的是「无名且无法归一」的，记录明细，避免静默
        dbg(`=== TOOLS in=${before}[${typesSeen}] out=${kept.length} dropped=${dropped.length}${dropped.length ? ' [' + dropped.join(',') + ']' : ''} ===\n`);
        if (kept.length === 0) delete body.tools; // 空数组上游可能拒，直接省略
      }

      const wantStream = !!body.stream;
      let text = '';

      // 1) 上游流式：先窥探首块，合法 SSE 就原样透传（保证客户端多轮状态机正确）
      if (!process.env.IG5_ONLY_FALLBACK && !ocDirect) {
        try {
          const up = await fetch(UP + '/responses', {
            method: 'POST', headers: { 'content-type': 'application/json' },
            body: JSON.stringify({ ...body, stream: wantStream })
          });
          if (wantStream && up.ok && up.body) {
            const reader = up.body.getReader();
            const first = await reader.read();
            const s0 = first.done ? '' : Buffer.from(first.value).toString('utf8');
            if (/^(event:|data:)/.test(s0)) {
              res.writeHead(200, { ...CORS, 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
              note(req, 200);
              res.write(s0);
              if (s0.includes('"response.completed"')) { /* 首块即完成（极短回复） */ }
              for (;;) { const n = await reader.read(); if (n.done) break; res.write(Buffer.from(n.value)); }
              dbg('=== UP STREAM passthrough ok ===\n');
              return res.end();
            }
            try { await reader.cancel(); } catch { }
            dbg(`=== UP STREAM degenerate, len=${s0.length} → 非流式重取 ===\n`);
          } else if (!wantStream && up.ok) {
            const j = await up.json();
            text = (j.output && j.output[0] && j.output[0].content && j.output[0].content[0] && j.output[0].content[0].text) || '';
            dbg(`=== UP ${up.status} textlen=${text.length} (non-stream) ===\n`);
            if (text) return json(res, 200, j, req);
          } else if (!up.ok) {
            dbg(`=== UP ${up.status} ===\n`);
          }
        } catch (e) { dbg(`=== UP ERR ${String(e && e.message || e)} ===\n`); }
      }

      // 2) 兜底 / 非流式合成
      text = text || await askOpencode(ocDirect ? body.model : (process.env.OC_MODEL || 'deepseek-v4.1-flash-free'),
        [{ role: 'system', content: PAYLOAD }, ...convoOf(body), { role: 'system', content: '工具不可用：请直接用文字回答当前问题，不要调用工具。' }].slice(-12));
      if (!text) text = '[bridge] 两个上游都没有返回内容，检查 8788 鉴权与 4097 是否在跑。';
      dbg(`=== FALLBACK/合成 textlen=${text.length} wantStream=${wantStream} ===\n`);

      if (!wantStream) {
        return json(res, 200, {
          id: 'resp_bridge_' + Date.now().toString(36), object: 'response', status: 'completed', model: body.model,
          output: [{ type: 'message', role: 'assistant', status: 'completed', content: [{ type: 'output_text', text, annotations: [] }] }],
          usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0 }
        }, req);
      }
      res.writeHead(200, { ...CORS, 'content-type': 'text/event-stream', 'cache-control': 'no-cache' });
      note(req, 200);
      const id = 'resp_bridge_' + Date.now().toString(36);
      const createdAt = Math.floor(Date.now() / 1000);
      const item = { id: id + '_msg', type: 'message', role: 'assistant', content: [{ type: 'text', text }] };
      const fin = {
        id, object: 'realtime.response', status: 'completed', created_at: createdAt, output: [item],
        usage: { input_tokens: 0, output_tokens: 0, total_tokens: 0, input_tokens_details: { cached_tokens: 0 }, output_tokens_details: { reasoning_tokens: 0 } },
        parallel_tool_calls: true
      };
      const ev = (t, o) => res.write('event: ' + t + '\ndata: ' + JSON.stringify({ type: t, ...o }) + '\n\n');
      ev('response.created', { response: { id, object: 'realtime.response', status: 'in_progress', created_at: createdAt } });
      ev('response.in_progress', { response: { id, object: 'realtime.response', status: 'in_progress' } });
      ev('response.output_item.added', { output_index: 0, item: { id: item.id, type: 'message', role: 'assistant', content: [] } });
      ev('response.content_part.added', { item_id: item.id, output_index: 0, content_index: 0, part: { type: 'text', text: '' } });
      ev('response.output_text.delta', { item_id: item.id, output_index: 0, content_index: 0, delta: text });
      ev('response.output_text.done', { item_id: item.id, output_index: 0, content_index: 0, text });
      ev('response.content_part.done', { item_id: item.id, output_index: 0, content_index: 0, part: { type: 'text', text } });
      ev('response.output_item.done', { output_index: 0, item });
      ev('response.completed', { response: fin });
      return res.end();
    }

    if (req.method === 'POST' && /\/chat\/completions$/.test(p)) {
      const body = JSON.parse((await readBody(req)) || '{}');
      body.model = body.model || 'deepseek-v4.1-flash';
      body.messages = [{ role: 'system', content: PAYLOAD }, ...(Array.isArray(body.messages) ? body.messages : [])];
      const up = await fetch(UP + '/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
      if (body.stream) {
        res.writeHead(up.status, { ...CORS, 'content-type': 'text/event-stream', 'cache-control': 'no-cache' }); note(req, up.status);
        for await (const c of up.body) res.write(c); return res.end();
      }
      return json(res, up.status, await up.json(), req);
    }

    return json(res, 404, { error: 'not found', path: p }, req);
  } catch (e) {
    return json(res, 500, { error: String((e && e.message) || e) }, req);
  }
});

server.listen(PORT, '127.0.0.1', () => console.log(`ig5-bridge v12 on ${PORT} -> ${UP}`));
