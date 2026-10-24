const B = 'http://127.0.0.1:8790/v1/responses';
async function t(model) {
  const r = await fetch(B, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ model, stream: true, input: '用一句话说明你是谁' })
  });
  const txt = await r.text();
  const m = txt.match(/"delta":\s*"((?:\\.|[^"\\])*)"/);
  const delta = m ? JSON.parse('"' + m[1] + '"') : '';
  console.log(model.padEnd(32), 'status=' + r.status, 'events=' + (txt.match(/^event: /gm) || []).length,
    'len=' + delta.length, 'head=' + JSON.stringify(delta.slice(0, 40)));
}
await t('deepseek-v4.1-flash');
await t('oc-deepseek-v4.1-flash-free');
