#!/usr/bin/env node
import { loadConfig } from '/Users/bsg/.npm-global/lib/node_modules/@leeguoo/zentao-mcp/src/config/store.js';
import { createClientFromCli } from '/Users/bsg/.npm-global/lib/node_modules/@leeguoo/zentao-mcp/src/zentao/client.js';

function usage() {
  console.error(`Usage: create_story_tasks_fast.mjs --story <id> [--execution <id>] [--deadline YYYY-MM-DD] [--backend yuh|chenyi] [--with-art] [--pool-id <id>]

Creates/reuses: product main task + backend/web/test (+ art) subtasks by ZenTao form, then prints JSON verification.`);
  process.exit(2);
}

function args(argv) {
  const out = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) usage();
    const key = a.slice(2);
    if (['with-art', 'dry-run'].includes(key)) out[key] = true;
    else out[key] = argv[++i];
  }
  if (!out.story) usage();
  return out;
}

function parseCookies(headers) {
  const jar = {};
  for (const h of headers.getSetCookie?.() || []) {
    const m = h.match(/^([^=]+)=([^;]*)/);
    if (m) jar[m[1]] = m[2];
  }
  return jar;
}
function cookieHeader(jar) { return Object.entries(jar).map(([k, v]) => `${k}=${v}`).join('; '); }
function accountOf(value) { return value && typeof value === 'object' ? value.account : value; }
function realOf(value) { return value && typeof value === 'object' ? value.realname : ''; }
function sleep(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
function isSunday(date) { return new Date(`${date}T00:00:00+08:00`).getDay() === 0; }
function addDays(date, days) {
  const d = new Date(`${date}T00:00:00+08:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}
function avoidSunday(date) { return isSunday(date) ? addDays(date, -1) : date; }
function nextWednesday() {
  const now = new Date();
  const cn = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Shanghai' }));
  const day = cn.getDay();
  const delta = ((3 - day + 7) % 7) || 7;
  cn.setDate(cn.getDate() + delta);
  return cn.toISOString().slice(0, 10);
}
function dateFromExecutionName(name) {
  const m = String(name || '').match(/[（(](\d{2})(\d{2})[）)]/);
  if (!m) return '';
  const y = new Date().toLocaleString('en-US', { timeZone: 'Asia/Shanghai', year: 'numeric' });
  return `${y}-${m[1]}-${m[2]}`;
}
function normalizeTask(t) {
  return {
    id: Number(t.id),
    parent: Number(t.parent || 0),
    name: t.name,
    type: t.type,
    subtype: t.subtype || '',
    assignedTo: accountOf(t.assignedTo),
    assignedToRealName: realOf(t.assignedTo) || t.assignedToRealName || '',
    deadline: t.deadline,
    status: t.status,
    story: Number(t.story || t.storyID || 0),
    execution: Number(t.execution || 0),
    deleted: t.deleted,
  };
}
function flattenTasks(tasks, out = []) {
  for (const t of tasks || []) {
    out.push(normalizeTask(t));
    if (t.children) flattenTasks(t.children, out);
  }
  return out;
}
function requiredAccounts({ isPlatform, backend, withArt }) {
  const base = ['cheny'];
  if (isPlatform) base.push(backend || 'NEED_BACKEND_CONFIRM', 'zhangxiaohui', 'linwq');
  else base.push(backend || 'chenlq', 'chenjie', 'chenyn');
  if (withArt) base.push('zhangqw');
  return base.filter(Boolean);
}
function extractAssignedOptions(html) {
  const m = html.match(/<select[^>]+name=['"]assignedTo\[\]['"][\s\S]*?<\/select>/i);
  const select = m?.[0] || '';
  const values = new Set();
  for (const opt of select.matchAll(/<option[^>]+value=['"]([^'"]*)['"][^>]*>/g)) values.add(opt[1]);
  return values;
}

async function main() {
  const opt = args(process.argv);
  const cfg = loadConfig({ env: process.env });
  const api = createClientFromCli({ argv: [], env: process.env });
  const base = cfg.zentaoUrl.replace(/\/+$/, '');
  let r = await fetch(`${base}/index.php?m=user&f=login&t=html`);
  let jar = parseCookies(r.headers);
  r = await fetch(`${base}/index.php?m=user&f=login&t=html`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded', Referer: `${base}/index.php?m=user&f=login&t=html`, Cookie: cookieHeader(jar) },
    body: new URLSearchParams({ account: cfg.zentaoAccount, password: cfg.zentaoPassword, keepLogin: 'on' }),
    redirect: 'manual',
  });
  jar = { ...jar, ...parseCookies(r.headers) };
  const cookie = cookieHeader(jar);

  const storyPayload = await api.request({ method: 'GET', path: `/api.php/v1/stories/${opt.story}` });
  const story = storyPayload.result || storyPayload;
  if (!story || !story.id) throw new Error(`story not found: ${opt.story}`);
  const executionID = opt.execution || Object.keys(story.executions || {})[0];
  if (!executionID) throw new Error('story has no execution; pass --execution');
  const executionName = story.executions?.[executionID]?.name || '';
  const title = story.title;
  const moduleID = String(story.module || 0);
  const source = story.source || 'customer';
  const category = story.category || 'feature';
  const isPlatform = String(story.productName || '').includes('平台部') || Number(story.product) === 4;
  if (isPlatform && !opt.backend) throw new Error('platform backend assignee required: pass --backend yuh or --backend chenyi');
  const testDeadline = opt.deadline || dateFromExecutionName(executionName) || (isPlatform ? nextWednesday() : '');
  if (!testDeadline) throw new Error('deadline required for non-platform story: pass --deadline YYYY-MM-DD');
  const devDeadline = avoidSunday(addDays(testDeadline, -2));
  const artDeadline = avoidSunday(addDays(devDeadline, -2));

  const createUrl = `${base}/index.php?m=task&f=create&executionID=${executionID}&storyID=${opt.story}&moduleID=${moduleID}&onlybody=yes`;
  const formRes = await fetch(createUrl, { headers: { Cookie: cookie, 'X-Requested-With': 'XMLHttpRequest', Referer: createUrl } });
  const formHtml = await formRes.text();
  const assignOptions = extractAssignedOptions(formHtml);
  const missing = requiredAccounts({ isPlatform, backend: opt.backend, withArt: Boolean(opt['with-art']) }).filter((a) => a !== 'NEED_BACKEND_CONFIRM' && !assignOptions.has(a));
  if (missing.length) throw new Error(`assignee not in task form options: ${missing.join(',')}`);

  async function listStoryTasks() {
    const json = await api.request({ method: 'GET', path: `/api.php/v1/executions/${executionID}/tasks`, query: { page: 1, limit: 500 } });
    return flattenTasks(json.result?.tasks || json.tasks || []).filter((t) => t.story === Number(opt.story) || String(t.name || '').includes(title));
  }
  let existing = await listStoryTasks();
  const byName = () => new Map(existing.filter((t) => !t.deleted && t.deleted !== '1').map((t) => [t.name, t]));

  async function createTask(task, parentID = '') {
    const found = byName().get(task.name);
    if (found) return { ...found, role: task.role, reused: true };
    if (opt['dry-run']) return { ...task, parent: parentID || 0, reused: false, dryRun: true };
    const fd = new FormData();
    const fields = {
      execution: String(executionID), category, pri: String(story.pri || 3), estimate: task.estimate || '0', left: task.estimate || '0',
      source, type: task.type, subtype: task.subtype || '', teamMember: '', module: moduleID, status: 'wait', story: String(opt.story),
      name: task.name, color: '', storyEstimate: String(story.estimate || 0), storyDesc: '', storyPri: String(story.pri || 3),
      estStarted: task.estStarted || '', deadline: task.deadline,
    };
    for (const [k, v] of Object.entries(fields)) fd.append(k, v);
    fd.append('assignedTo[]', task.assignedTo);
    fd.append('desc', `关联需求 #${opt.story}：${title}。\n截止日期：${task.deadline}。`);
    fd.append('mailto[]', '');
    if (parentID) fd.append('parent', String(parentID));
    const res = await fetch(createUrl, { method: 'POST', headers: { Cookie: cookie, 'X-Requested-With': 'XMLHttpRequest', Referer: createUrl }, body: fd, redirect: 'manual' });
    const text = await res.text();
    if (!text.includes('保存成功')) throw new Error(`create failed: ${task.name}; ${text.slice(0, 300).replace(/\s+/g, ' ')}`);
    await sleep(400);
    existing = await listStoryTasks();
    const created = byName().get(task.name);
    if (!created) throw new Error(`created but not found in execution list: ${task.name}`);
    return { ...created, role: task.role, reused: false };
  }

  const mainName = `【需求单】${title}`;
  const main = await createTask({ role: '主任务', name: mainName, type: 'design', assignedTo: story.assignedTo?.account || 'cheny', deadline: testDeadline });
  const childSpecs = [
    { role: '后端', name: `【开发单】${title} --账服`, type: 'devel', subtype: isPlatform ? 'zf' : '', assignedTo: opt.backend || 'chenlq', deadline: devDeadline },
    { role: '前端', name: `【开发单】${title} --Web`, type: 'web', assignedTo: isPlatform ? 'zhangxiaohui' : 'chenjie', deadline: devDeadline },
    { role: '测试', name: `【测试单】${title} 测试`, type: 'discuss', assignedTo: isPlatform ? 'linwq' : 'chenyn', deadline: testDeadline },
  ];
  if (opt['with-art']) childSpecs.push({ role: '美术', name: `【美术单】${title} 美术`, type: 'study', assignedTo: 'zhangqw', deadline: artDeadline });
  const children = [];
  for (const spec of childSpecs) children.push(await createTask(spec, main.id));

  if (opt['pool-id'] && !opt['dry-run']) {
    const editUrl = `${base}/index.php?m=pool&f=edit&id=${opt['pool-id']}&t=html`;
    const poolPage = await fetch(editUrl, { headers: { Cookie: cookie, 'X-Requested-With': 'XMLHttpRequest', Referer: editUrl } }).then((x) => x.text());
    const val = (name) => (poolPage.match(new RegExp(`name=['"]${name}['"][^>]*value=['"]([^'"]*)`, 'i')) || [])[1] || '';
    const selected = (name) => (poolPage.match(new RegExp(`<select[^>]+name=['"]${name}['"][\\s\\S]*?<option value=['"]([^'"]*)['"][^>]*selected`, 'i')) || [])[1] || '';
    const txt = (name) => (poolPage.match(new RegExp(`<textarea[^>]+name=['"]${name}['"][^>]*>([\\s\\S]*?)<\\/textarea>`, 'i')) || [])[1] || '';
    const params = new URLSearchParams({
      category: selected('category'), priority: selected('priority'), status: selected('status') || '1', title: val('title'), desc: txt('desc'),
      deliveryDate: val('deliveryDate'), submitter: selected('submitter'), phpGroup: selected('phpGroup'), pm: selected('pm'),
      execution: String(executionID), taskID: String(main.id), remark: txt('remark'),
    });
    await fetch(editUrl, { method: 'POST', headers: { Cookie: cookie, Referer: editUrl, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded' }, body: params, redirect: 'manual' });
  }

  existing = await listStoryTasks();
  const wanted = [main.name, ...childSpecs.map((x) => x.name)];
  const finalTasks = existing.filter((t) => wanted.includes(t.name)).sort((a, b) => a.id - b.id);
  console.log(JSON.stringify({ story: Number(opt.story), execution: Number(executionID), executionName, deadline: { test: testDeadline, dev: devDeadline, art: opt['with-art'] ? artDeadline : null }, tasks: finalTasks }, null, 2));
}

main().catch((err) => { console.error(err.stack || err.message); process.exit(1); });
