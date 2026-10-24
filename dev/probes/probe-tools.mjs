const UP = 'http://127.0.0.1:8788/v1/responses';
const flat = [{ type: 'function', name: 'shell', description: 'run', parameters: { type: 'object', properties: { command: { type: 'string' } }, required: ['command'] } }];
const nested = [{ type: 'function', function: { name: 'shell', description: 'run', parameters: { type: 'object', properties: { command: { type: 'string' } }, required: ['command'] } } }];
async function t(name, tools) {
  const r = await fetch(UP, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: 'deepseek-v4.1-flash', input: 'hi', stream: false, tools }) });
  const j = await r.json();
  const txt = j && j.output && j.output[0] && j.output[0].content && j.output[0].content[0] && j.output[0].content[0].text;
  console.log(name.padEnd(10), 'status=' + r.status, 'text=' + JSON.stringify((txt || '').slice(0, 40)), 'err=' + JSON.stringify(j.error ? String(JSON.stringify(j).slice(0, 120)) : '-'));
}
await t('flat', flat);
await t('nested', nested);
