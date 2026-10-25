// dev/repro_responses_break.mjs —— 复现 /v1/responses 透传时上游断流
// 假上游在 function_call 输出项刚开始时 destroy socket，检查桥是否补 response.failed。
import http from 'node:http';
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BRIDGE = path.join(HERE, '..', 'src', 'ig5-bridge.mjs');
const UP = 18789, BP = 18791;

const up = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    res.writeHead(200, { 'content-type': 'text/event-stream' });
    res.write('event: response.created\ndata: {"type":"response.created","response":{"id":"resp_x","status":"in_progress"}}\n\n');
    res.write('event: response.output_item.added\ndata: {"type":"response.output_item.added","output_index":0,"item":{"id":"fc_1","type":"function_call","name":"read"}}\n\n');
    setTimeout(() => req.socket.destroy(), 120);
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
  const req = http.request({ host: '127.0.0.1', port: BP, path: '/v1/responses', method: 'POST',
    headers: { 'content-type': 'application/json' } }, (res) => {
    res.on('data', (c) => seen.push(String(c)));
    res.on('end', () => resolve(res.statusCode));   // 只有 end 才算收完，否则会提前 kill 子进程
    res.on('error', (e) => seen.push('[client error] ' + e.message));
  });
  req.on('error', (e) => { seen.push('[client error] ' + e.message); resolve(0); });
  req.end(JSON.stringify({ model: 'deepseek-v4.1-flash', stream: true, input: 'hi' }));
});

const got = seen.join('');
const evCount = (name) => (got.match(new RegExp('event: ' + name + '\\n', 'g')) || []).length;
console.log(JSON.stringify({
  status,
  bytes: got.length,
  ev_created: evCount('response.created'),
  ev_function_call_added: evCount('response.output_item.added'),
  ev_completed: evCount('response.completed'),
  ev_failed: evCount('response.failed'),
  tail: got.slice(-110).replace(/\n/g, '\\n'),
}, null, 2));
child.kill(); up.close();
