// Push local commits to GitHub via the REST Git Data API (works when github.com:443 is blocked but api.github.com is reachable)
import { execSync } from 'node:child_process';
import fs from 'node:fs';

const TOKEN = process.env.GH_TOKEN;
if (!TOKEN) { console.error('GH_TOKEN missing'); process.exit(2); }
const OWNER = 'Bailan766', REPO = 'wb-armor', BRANCH = 'main';
const API = 'https://api.github.com';
const H = { 'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json', 'User-Agent': 'wb-armor-push', 'Content-Type': 'application/json' };
const git = (cmd) => execSync('git ' + cmd, { cwd: process.cwd(), encoding: 'utf8' }).trim();
async function api(method, path, body) {
  const r = await fetch(API + path, { method, headers: H, body: body ? JSON.stringify(body) : undefined });
  const t = await r.text();
  if (!r.ok) throw new Error(`${method} ${path} -> ${r.status} ${t.slice(0, 300)}`);
  return t ? JSON.parse(t) : null;
}

const localHead = git('rev-parse HEAD');
const remote = await api('GET', `/repos/${OWNER}/${REPO}/git/ref/heads/${BRANCH}`);
const remoteSha = remote.object.sha;
console.log('local HEAD =', localHead.slice(0, 7), ' remote =', remoteSha.slice(0, 7));

const commits = git(`rev-list --reverse ${remoteSha}..${localHead}`).split('\n').filter(Boolean);
console.log('commits to replay:', commits.length);
if (!commits.length) { console.log('nothing to push'); process.exit(0); }

let baseSha = remoteSha;
for (const c of commits) {
  const msg = git(`log -1 --pretty=%B ${c}`);
  const names = git(`diff --name-status ${c}~1 ${c}`).split('\n').filter(Boolean);
  const entries = [];
  for (const line of names) {
    const parts = line.split('\t');
    const st = parts[0][0];
    const p = parts[parts.length - 1];
    if (st === 'D') { entries.push({ path: p, mode: '100644', type: 'blob', sha: null }); continue; }
    entries.push({ path: p, mode: '100644', type: 'blob', content: fs.readFileSync(p, 'utf8') });
  }
  const baseTree = (await api('GET', `/repos/${OWNER}/${REPO}/git/commits/${baseSha}`)).tree.sha;
  let tree;
  try { tree = await api('POST', `/repos/${OWNER}/${REPO}/git/trees`, { base_tree: baseTree, tree: entries }); }
  catch (e) { console.error('TREE FAIL', JSON.stringify({ base_tree: baseTree, n: entries.length, sample: entries.slice(0,3) })); throw e; }
  const nc = await api('POST', `/repos/${OWNER}/${REPO}/git/commits`, { message: msg, tree: tree.sha, parents: [baseSha] });
  baseSha = nc.sha;
  console.log('  replayed', c.slice(0, 7), '->', nc.sha.slice(0, 7), `(${entries.length} paths)`);
}

await api('PATCH', `/repos/${OWNER}/${REPO}/git/refs/heads/${BRANCH}`, { sha: baseSha, force: false });
console.log('branch updated ->', baseSha.slice(0, 7));

const tagName = process.env.TAG_NAME;
if (tagName) {
  try {
    await api('POST', `/repos/${OWNER}/${REPO}/git/refs`, { ref: `refs/tags/${tagName}`, sha: baseSha });
    console.log('tag created:', tagName, '->', baseSha.slice(0, 7));
  } catch (e) {
    if (String(e.message).includes('422')) {
      await api('PATCH', `/repos/${OWNER}/${REPO}/git/refs/tags/${tagName}`, { sha: baseSha, force: true });
      console.log('tag moved:', tagName, '->', baseSha.slice(0, 7));
    } else throw e;
  }
}
