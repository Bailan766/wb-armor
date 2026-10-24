const B = 'http://127.0.0.1:8790/v1/responses';
async function call(label, input) {
  const r = await fetch(B, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: 'deepseek-v4.1-flash', stream: true, input }) });
  const txt = await r.text();
  const evs = (txt.match(/^event: /gm) || []).length;
  const ds = [...txt.matchAll(/"delta":\s*"((?:\\.|[^"\\])*)"/g)].map(m => { try { return JSON.parse('"' + m[1] + '"'); } catch { return ''; } });
  const out = ds.join('');
  console.log(label.padEnd(8), 'status=' + r.status, 'events=' + evs, 'len=' + out.length, 'head=' + JSON.stringify(out.slice(0, 50)));
  return out;
}
await call('turn1', '记住：我叫甲。只回 OK');
await call('turn2', [
  { type: 'message', role: 'user', content: [{ type: 'input_text', text: '记住：我叫甲。只回 OK' }] },
  { type: 'message', role: 'assistant', content: [{ type: 'output_text', text: 'OK' }] },
  { type: 'message', role: 'user', content: [{ type: 'input_text', text: '我叫什么？只回名字' }] }
]);
