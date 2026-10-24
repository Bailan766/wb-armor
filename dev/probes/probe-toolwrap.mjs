const B = 'http://127.0.0.1:8790/v1/responses';
async function t(label, tools) {
  const r = await fetch(B, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ model: 'deepseek-v4.1-flash', stream: true, tools, input: '只用工具写文件，路径 C:/temp/a.txt' })
  });
  const txt = await r.text();
  console.log(label, 'status=' + r.status, 'len=' + txt.length, 'head=' + JSON.stringify(txt.slice(0, 160)));
}
const fn = { type: 'function', name: 'write_file', description: 'w', parameters: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] } };
const custom = { type: 'custom', name: 'apply_patch', description: 'patch', format: { type: 'grammar', syntax: 'lark', definition: 'start: /.+/' } };
const ns = { type: 'namespace', name: 'shell', description: 'run shell' };
await t('fn-only   ', [fn]);
await t('fn+custom ', [fn, custom]);
await t('fn+custom+ns', [fn, custom, ns]);
