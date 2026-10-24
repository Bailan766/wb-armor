const B = 'http://127.0.0.1:4097';
const j = (r) => r.json();
const s = await fetch(B + '/session', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ title: 'ig5-probe' }) }).then(j);
console.log('session', s.id, 'keys=' + Object.keys(s).join(','));
const body = {
  model: { providerID: 'opencode', modelID: 'deepseek-v4.1-flash-free' },
  parts: [{ type: 'text', text: '只回四个字：免费可用' }]
};
const r = await fetch(`${B}/session/${s.id}/message`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
const t = await r.text();
console.log('message status=' + r.status);
console.log(t.slice(0, 700));
