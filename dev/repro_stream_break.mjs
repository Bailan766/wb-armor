// dev/repro_stream_break.mjs —— 复现：上游 SSE 断流时桥的表现
// 起一个假上游(18788)，在 tool_use 块中途 destroy socket；再起桥(18790)指向它，
// 用一个 /v1/messages 流式请求打过去，看客户端到底收到什么、桥是否二次写响应。
import http from 'node:http';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE = path.join(HERE, '..', 'src', 'ig5-bridge.mjs');
const UP = 18788, BP = 18790;

const up = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    res.writeHead(200, { 'content-type': 'text/event-stream' });
    // 一个合法的 message_start + 一个已开始但永不完成的 tool_use
    res.write('event: message_start\ndata: {"type":"message_start","message":{"id":"msg_x","role":"assistant","content":[]}}\n\n');
    res.write('event: content_block_start\ndata: {"type":"content_block_start","index":0,"content_block":{"type":"tool_use","id":"toolu_A","name":"read"}}\n\n');
    setTimeout(() => { req.socket.destroy(); }, 120); // ← 中途断流
  });
});
await new Promise((r) => up.listen(UP, '127.0.0.1', r));

const child = spawn(process.execPath, [BRIDGE], {
  env: { ...process.env, IG5_PORT: String(BP), IG5_UPSTREAM: `http://127.0.0.1:${UP}/v1` },
  stdio: ['ignore', 'inherit', 'inherit'],
});
await new Promise((r) => setTimeout(r, 900));

const seen = [];
const status = await new Promise((resolve) => {
  const req = http.request({ host: '127.0.0.1', port: BP, path: '/v1/messages', method: 'POST',
    headers: { 'content-type': 'application/json' } }, (res) => {
    res.on('data', (c) => seen.push(String(c)));
    res.on('end', () => resolve(res.statusCode));   // 只有 end 才算收完，否则会提前 kill 子进程
    res.on('error', (e) => seen.push('[client error] ' + e.message));
  });
  req.on('error', (e) => { seen.push('[client error] ' + e.message); resolve(0); });
  req.end(JSON.stringify({ model: 'deepseek-v4.1-flash', stream: true, max_tokens: 32,
    messages: [{ role: 'user', content: 'hi' }] }));
});

const got = seen.join('');
const evCount = (name) => (got.match(new RegExp('event: ' + name + '\\n', 'g')) || []).length;
console.log(JSON.stringify({
  status,
  bytes: got.length,
  events_message_start: evCount('message_start'),
  events_tool_use_start: evCount('content_block_start'),
  events_message_stop: evCount('message_stop'),
  events_error: evCount('error'),
  fallback_text: /\[bridge\]|opencode/i.test(got),
  tail: got.slice(-120).replace(/\n/g, '\\n'),
}, null, 2));
child.kill(); up.close();
