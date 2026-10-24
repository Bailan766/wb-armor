// 统一日志：JSONL 追加写 + 按大小轮转 + 敏感字段脱敏 + 请求级 rid
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const LOG_DIR = process.env.WBA_LOG_DIR || path.join(HERE, '..', 'logs');
const MAX_BYTES = Number(process.env.WBA_LOG_MAX || 5 * 1024 * 1024);
const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };
const MIN = LEVELS[(process.env.WBA_LOG_LEVEL || 'info').toLowerCase()] ?? LEVELS.info;
const SECRET = /^(authorization|api[-_]?key|token|access[-_]?token|refresh[-_]?token|secret|password|cookie)$/i;

function redact(v, depth = 0) {
  if (depth > 4 || v == null) return v;
  if (Array.isArray(v)) return v.slice(0, 20).map((x) => redact(x, depth + 1));
  if (typeof v === 'object') {
    const out = {};
    for (const [k, val] of Object.entries(v)) {
      out[k] = SECRET.test(k) ? '***' : redact(val, depth + 1);
    }
    return out;
  }
  if (typeof v === 'string' && v.length > 2000) return v.slice(0, 2000) + '…';
  return v;
}

function rotate(file) {
  try {
    if (!fs.existsSync(file)) return;
    if (fs.statSync(file).size < MAX_BYTES) return;
    const old = file.replace(/\.log$/, '') + '.1.log';
    if (fs.existsSync(old)) fs.unlinkSync(old);
    fs.renameSync(file, old);
  } catch { }
}

export function createLogger(component) {
  fs.mkdirSync(LOG_DIR, { recursive: true });
  const day = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  const file = path.join(LOG_DIR, `${component}-${day}.log`);
  rotate(file);

  const write = (level, msg, fields) => {
    if (LEVELS[level] < MIN) return;
    const rec = { ts: new Date().toISOString(), level, comp: component, msg, ...redact(fields || {}) };
    try { fs.appendFileSync(file, JSON.stringify(rec) + '\n'); } catch { }
    if (process.env.WBA_LOG_STDERR === '1') process.stderr.write(JSON.stringify(rec) + '\n');
  };

  const log = {
    file,
    rid: () => 'r' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    debug: (msg, f) => write('debug', msg, f),
    info: (msg, f) => write('info', msg, f),
    warn: (msg, f) => write('warn', msg, f),
    error: (msg, f) => write('error', msg, f),
    child(bind) {
      const c = createLogger(component);
      const wrap = (lv) => (msg, f) => write(lv, msg, { ...bind, ...(f || {}) });
      return { ...c, debug: wrap('debug'), info: wrap('info'), warn: wrap('warn'), error: wrap('error') };
    }
  };
  return log;
}
