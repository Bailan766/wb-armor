const BASE = 'http://127.0.0.1:8790/v1/responses';

async function run(name, body) {
  const r = await fetch(BASE, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body)
  });
  const text = await r.text();
  const events = (text.match(/^event: /gm) || []).length;
  const byteish = /^\d+(,\d+){10,}/.test(text.trim());
  console.log(`${name.padEnd(26)} status=${r.status} len=${text.length} events=${events} byteList=${byteish} head="${text.slice(0, 40).replace(/\n/g, '\\n')}"`);
  return { events, byteish, text };
}

const tools = [{ type: 'function', name: 'shell', description: 'run', parameters: { type: 'object', properties: { command: { type: 'string' } } } }];

await run('A instructions only', { model: 'deepseek-v4.1-flash', input: 'hi', stream: true, instructions: 'sys' });
await run('B tools only', { model: 'deepseek-v4.1-flash', input: 'hi', stream: true, tools });
await run('C developer only', { model: 'deepseek-v4.1-flash', stream: true, input: [{ type: 'message', role: 'developer', content: [{ type: 'input_text', text: 'sys' }] }, { type: 'message', role: 'user', content: [{ type: 'input_text', text: 'hi' }] }] });
await run('D dev+tools', { model: 'deepseek-v4.1-flash', stream: true, tools, input: [{ type: 'message', role: 'developer', content: [{ type: 'input_text', text: 'sys' }] }, { type: 'message', role: 'user', content: [{ type: 'input_text', text: 'hi' }] }] });
