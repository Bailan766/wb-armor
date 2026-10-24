const BASE = 'https://opencode.ai/zen/v1';
const msg = [{ role: 'user', content: '只回四个字：免费可用' }];
async function go(label, extra) {
  const r = await fetch(BASE + '/chat/completions', {
    method: 'POST',
    headers: { 'content-type': 'application/json', ...extra },
    body: JSON.stringify({ model: 'deepseek-v4.1-flash-free', messages: msg, stream: false })
  });
  const t = await r.text();
  console.log('---', label, 'status=' + r.status);
  console.log(t.slice(0, 400));
}
await go('no-headers', {});
await go('ua-opencode', { 'user-agent': 'opencode/1.18.5' });
await go('ua+accept', { 'user-agent': 'opencode/1.18.5', accept: 'application/json', 'x-opencode-client': 'cli' });
