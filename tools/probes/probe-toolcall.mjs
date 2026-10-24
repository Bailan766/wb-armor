const B = 'http://127.0.0.1:8790/v1/responses';
const tools = [{
  type: 'function', name: 'write_file', description: 'write a file',
  parameters: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] }
}];
const r = await fetch(B, {
  method: 'POST', headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ model: 'deepseek-v4.1-flash', stream: true, tools, input: '把 hi 写入 C:/temp/x.txt，用 write_file 工具' })
});
const txt = await r.text();
console.log('status=' + r.status, 'events=' + (txt.match(/^event: /gm) || []).length);
const types = [...new Set([...txt.matchAll(/"type":\s*"([a-z_.]+)"/g)].map(m => m[1]))];
console.log('types=' + types.join(','));
const fc = txt.match(/"type":\s*"function_call"[\s\S]{0,200}/);
console.log('function_call=' + (fc ? fc[0].replace(/\s+/g, ' ').slice(0, 180) : 'NONE'));
const d = txt.match(/"delta":\s*"((?:\\.|[^"\\])*)"/);
console.log('text=' + JSON.stringify(d ? d[1].slice(0, 80) : ''));
