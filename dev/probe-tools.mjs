const H = 'http://127.0.0.1:8790/health';
const B = 'http://127.0.0.1:8790/v1/responses';
const U = 'http://127.0.0.1:8788/v1/responses';
const tools = [{ type: 'function', name: 'write_file', description: 'write a file to disk',
  parameters: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] } }];
const body = (m) => JSON.stringify({ model: m, stream: true, tools, input: '用 write_file 把 hi 写入 C:/temp/x.txt' });
const stat = async () => (await (await fetch(H)).json());

async function probe(label, url, model) {
  const before = await stat();
  const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: body(model) });
  const t = await r.text();
  const after = await stat();
  const evs = (t.match(/^event: /gm) || []).length;
  const fc = /"type":\s*"function_call"/.test(t);
  const fcArgs = [...t.matchAll(/"name":\s*"([^"]+)"/g)].map(m => m[1]).slice(0, 3);
  console.log(`${label.padEnd(18)} status=${r.status} events=${evs} function_call=${fc} names=${JSON.stringify(fcArgs)} fallbacksDelta=${(after.fallbacks || 0) - (before.fallbacks || 0)} len=${t.length}`);
}
await probe('upstream-8788', U, 'deepseek-v4.1-flash');
await probe('bridge-8790', B, 'deepseek-v4.1-flash');
await probe('bridge-oc-free', B, 'oc-deepseek-v4.1-flash-free');
