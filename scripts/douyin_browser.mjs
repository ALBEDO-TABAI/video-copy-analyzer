#!/usr/bin/env node
/**
 * Visit a Douyin video page in a local Chromium browser and extract
 * aweme/detail play URLs. Stdout is a single JSON object.
 *
 * Usage: node douyin_browser.mjs <douyin-url>
 */
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, rmSync } from 'node:fs';
import net from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const TARGET = process.argv[2];
if (!TARGET) {
  process.stderr.write('usage: node douyin_browser.mjs <douyin-url>\n');
  process.exit(2);
}

const WAIT_MS = Number(process.env.DOUYIN_BROWSER_TIMEOUT_MS || 28000);
const HEADED = process.env.DOUYIN_BROWSER_HEADED === '1';
const ATTACH = process.env.DOUYIN_CDP_URL || '';

function log(msg) {
  process.stderr.write(`${msg}\n`);
}

function browserCandidates() {
  const extra = [process.env.DOUYIN_BROWSER, process.env.CHROME_PATH, process.env.EDGE_PATH].filter(Boolean);
  const mac = [
    '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ];
  const linux = [
    'microsoft-edge',
    'microsoft-edge-stable',
    'google-chrome',
    'google-chrome-stable',
    'chromium',
    'chromium-browser',
  ];
  const win = [
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  ];
  return [...extra, ...mac, ...linux, ...win];
}

function which(cmd) {
  const path = process.env.PATH || '';
  const ext = process.platform === 'win32' ? ['.exe', ''] : [''];
  for (const dir of path.split(process.platform === 'win32' ? ';' : ':')) {
    for (const e of ext) {
      const full = join(dir, cmd + e);
      if (existsSync(full)) return full;
    }
  }
  return null;
}

function findBrowser() {
  for (const c of browserCandidates()) {
    if (!c) continue;
    if (c.includes('/') || c.includes('\\')) {
      if (existsSync(c)) return c;
    } else {
      const found = which(c);
      if (found) return found;
    }
  }
  return null;
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close((err) => (err ? reject(err) : resolve(port)));
    });
    server.on('error', reject);
  });
}

async function waitJson(url, tries = 50) {
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(url, { signal: AbortSignal.timeout(400) });
      if (res.ok) return res.json();
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`CDP not ready: ${url}`);
}

function cdpCall(ws, id, method, params = {}, timeout = 15000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`CDP timeout ${method}`)), timeout);
    const onMsg = (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (msg.id !== id) return;
      clearTimeout(timer);
      ws.removeEventListener('message', onMsg);
      if (msg.error) reject(new Error(JSON.stringify(msg.error)));
      else resolve(msg.result);
    };
    ws.addEventListener('message', onMsg);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

function pickFromDetail(raw) {
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  const detail = data.aweme_detail;
  if (!detail || typeof detail !== 'object') return null;
  const video = detail.video || {};
  const urls = [];
  for (const key of ['play_addr_h264', 'play_addr', 'play_addr_265']) {
    const list = video[key]?.url_list;
    if (Array.isArray(list)) urls.push(...list.filter(Boolean));
  }
  const uri = video.play_addr?.uri || video.play_addr_h264?.uri || '';
  if (!urls.length && !uri) return null;
  return {
    aweme_id: String(detail.aweme_id || ''),
    desc: String(detail.desc || ''),
    uri,
    duration_ms: Number(video.duration || 0),
    play_urls: [...new Set(urls)],
  };
}

async function extractViaCdp(cdpOrigin, pageUrl) {
  const version = await waitJson(`${cdpOrigin}/json/version`);
  const browserWs = new WebSocket(version.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    browserWs.addEventListener('open', res);
    browserWs.addEventListener('error', rej);
  });

  const created = await cdpCall(browserWs, 1, 'Target.createTarget', { url: 'about:blank' });
  const listed = await fetch(`${cdpOrigin}/json/list`).then((r) => r.json());
  const page = listed.find((t) => t.id === created.targetId);
  if (!page) throw new Error('failed to create browser tab');

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener('open', res);
    ws.addEventListener('error', rej);
  });

  const detailIds = new Set();
  const finishedIds = [];
  const vodUrls = [];
  let nextId = 200;

  ws.addEventListener('message', (ev) => {
    let msg;
    try {
      msg = JSON.parse(ev.data);
    } catch {
      return;
    }
    if (msg.method === 'Network.responseReceived') {
      const url = msg.params.response?.url || '';
      if (url.includes('/aweme/v1/web/aweme/detail/')) {
        detailIds.add(msg.params.requestId);
      }
      if (url.includes('douyinvod.com') && (msg.params.response.mimeType || '').includes('video')) {
        vodUrls.push(url);
      }
    }
    if (msg.method === 'Network.loadingFinished' && detailIds.has(msg.params.requestId)) {
      finishedIds.push(msg.params.requestId);
    }
  });

  await cdpCall(ws, 10, 'Network.enable');
  await cdpCall(ws, 11, 'Page.enable');

  const awemeId = (pageUrl.match(/\/(?:video|note)\/(\d+)/) || pageUrl.match(/modal_id=(\d+)/) || [])[1];
  const targets = [pageUrl];
  if (awemeId) {
    targets.push(`https://www.douyin.com/video/${awemeId}`);
    targets.push(`https://www.douyin.com/jingxuan?modal_id=${awemeId}`);
  }

  await cdpCall(ws, 12, 'Page.navigate', { url: 'https://www.douyin.com/' });
  await new Promise((r) => setTimeout(r, 1500));

  let found = null;
  for (const target of [...new Set(targets)]) {
    if (found) break;
    log(`navigate ${target}`);
    await cdpCall(ws, nextId++, 'Page.navigate', { url: target });
    const hopDeadline = Date.now() + Math.min(12000, WAIT_MS);
    while (!found && Date.now() < hopDeadline) {
      while (finishedIds.length && !found) {
        const requestId = finishedIds.shift();
        try {
          const body = await cdpCall(ws, nextId++, 'Network.getResponseBody', { requestId });
          const text = body.base64Encoded
            ? Buffer.from(body.body, 'base64').toString('utf8')
            : body.body;
          found = pickFromDetail(text);
          if (found) log(`got aweme detail (${text.length} bytes)`);
        } catch (err) {
          log(`detail body skipped: ${err.message}`);
        }
      }
      await new Promise((r) => setTimeout(r, 200));
    }
  }

  const leftoverDeadline = Date.now() + 3000;
  while (!found && Date.now() < leftoverDeadline) {
    while (finishedIds.length && !found) {
      const requestId = finishedIds.shift();
      try {
        const body = await cdpCall(ws, nextId++, 'Network.getResponseBody', { requestId });
        const text = body.base64Encoded
          ? Buffer.from(body.body, 'base64').toString('utf8')
          : body.body;
        found = pickFromDetail(text);
        if (found) log(`got aweme detail (${text.length} bytes)`);
      } catch (err) {
        log(`detail body skipped: ${err.message}`);
      }
    }
    await new Promise((r) => setTimeout(r, 200));
  }

  if (!found && vodUrls.length) {
    log(`fallback to ${vodUrls.length} captured media URL(s)`);
    found = { aweme_id: '', desc: '', uri: '', duration_ms: 0, play_urls: [...new Set(vodUrls)] };
  }

  if (!found) {
    try {
      const perf = await cdpCall(ws, nextId++, 'Runtime.evaluate', {
        expression: `(() => ({
          title: document.title,
          href: location.href,
          vod: performance.getEntriesByType('resource').map(e => e.name).filter(u => u.includes('douyinvod.com')).slice(0, 8)
        }))()`,
        returnByValue: true,
      });
      const value = perf.result?.value || {};
      log(`page title=${value.title || ''} href=${value.href || ''}`);
      if (value.vod?.length) {
        found = { aweme_id: '', desc: '', uri: '', duration_ms: 0, play_urls: value.vod };
      }
    } catch (err) {
      log(`page probe failed: ${err.message}`);
    }
  }

  try {
    await cdpCall(browserWs, 99, 'Target.closeTarget', { targetId: created.targetId });
  } catch {}
  try { ws.close(); } catch {}
  try { browserWs.close(); } catch {}

  if (!found) throw new Error('page loaded but aweme detail had no play URL');
  return found;
}

function launchBrowser(bin, port, profile) {
  const args = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-sync',
    'about:blank',
  ];
  if (!HEADED) args.unshift('--headless=new', '--disable-gpu');
  return spawn(bin, args, {
    stdio: 'ignore',
    windowsHide: true,
  });
}

function killTree(child) {
  if (!child || child.killed) return;
  try { child.kill('SIGTERM'); } catch {}
  setTimeout(() => {
    try { child.kill('SIGKILL'); } catch {}
  }, 400);
}

let child = null;
let profile = null;

try {
  let origin = ATTACH.replace(/\/$/, '');
  if (!origin) {
    const bin = findBrowser();
    if (!bin) {
      throw new Error('no Chrome/Edge/Chromium found; set DOUYIN_BROWSER to the binary path');
    }
    const port = await freePort();
    profile = mkdtempSync(join(tmpdir(), 'douyin-cdp-'));
    log(`using browser: ${bin}`);
    child = launchBrowser(bin, port, profile);
    origin = `http://127.0.0.1:${port}`;
  } else {
    log(`attaching CDP ${origin}`);
  }

  const result = await extractViaCdp(origin, TARGET);
  process.stdout.write(`${JSON.stringify(result)}\n`);
} catch (err) {
  process.stderr.write(`✗ ${err.message || err}\n`);
  process.exitCode = 1;
} finally {
  killTree(child);
  if (profile) {
    setTimeout(() => {
      try { rmSync(profile, { recursive: true, force: true }); } catch {}
      process.exit(process.exitCode || 0);
    }, 600);
  }
}
