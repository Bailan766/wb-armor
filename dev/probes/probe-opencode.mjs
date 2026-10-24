const BASE = 'https://opencode.ai/zen/v1';
const body = (model) => JSON.stringify({ model, messages: [{ role: 'user', content: '只回四个字：免费可用' }], stream: false });

for (const model of ['deepseek-v4.1-flash-free', 'glm-5.3-flash-free', 'big-pickle']) {
  try {
    const r = await fetch(BASE + '/chat/completions', {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: body(model)
    });
    const t = await r.text();
    let text = '';
    try { const j = JSON.parse(t); text = (j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content) || ''; } catch { }
    console.log(model.padEnd(26), 'status=' + r.status, 'text=' + JSON.stringify(text.slice(0, 30)), 'raw=' + JSON.stringify(t.slice(0, 100)));
  } catch (e) {
    console.log(model.padEnd(26), 'ERR ' + String(e && e.message || e));
  }
}
