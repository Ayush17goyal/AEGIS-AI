// Actual browser + HTTP integration against isolated local servers and synthetic DB.
// PLAYWRIGHT_MODULE may point to an existing Playwright installation.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdtemp, unlink, rmdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import assert from 'node:assert/strict';
import net from 'node:net';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const port = () => new Promise((resolve, reject) => {
  const server = net.createServer(); server.on('error', reject);
  server.listen(0, '127.0.0.1', () => { const value = server.address().port; server.close(() => resolve(value)); });
});
const apiPort = await port();
const webPort = await port();
const temp = await mkdtemp(join(tmpdir(), 'aegis-studio-e2e-'));
const dbFile = join(temp, 'synthetic.db');
const env = { ...process.env, DATABASE_URL: `sqlite:///${dbFile.replaceAll('\\', '/')}`, LLM_PROVIDER: 'mock',
  AEGIS_PIPELINE: 'approved', AEGIS_DEMO_MODE: 'true', AEGIS_ENV: 'development', DEMO_PASSWORD: 'AegisDemo!2026' };
const backend = spawn(process.env.PYTHON || 'python', ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', String(apiPort)], { env, stdio: 'ignore' });
// Vite's project proxy targets 8000; intercept /api in the test browser so this
// isolated test never calls an already-running user's backend.
const frontend = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', String(webPort), '--strictPort'], { stdio: 'ignore' });
let browser;
let checks = 0;
async function ready(url) {
  for (let i = 0; i < 80; i++) {
    try { if ((await fetch(url)).ok) return; } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error('Isolated test server did not become ready');
}
try {
  await Promise.all([ready(`http://127.0.0.1:${apiPort}/health`), ready(`http://127.0.0.1:${webPort}`)]);
  browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) });
  const page = await browser.newPage();
  await page.route('**/api/**', async (route) => {
    const source = new URL(route.request().url());
    const response = await route.fetch({ url: `http://127.0.0.1:${apiPort}${source.pathname}${source.search}` });
    await route.fulfill({ response });
  });
  const login = await fetch(`http://127.0.0.1:${apiPort}/api/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 'bob', password: 'AegisDemo!2026' }) });
  const { token } = await login.json();
  assert.ok(token); checks++;
  await page.addInitScript((token) => { sessionStorage.setItem('aegis-token', token); localStorage.setItem('aegis-theme', 'light'); }, token);
  let executions = 0;
  page.on('request', (request) => { if (request.method() === 'POST' && /\/api\/(chat|demos\/run)$/.test(new URL(request.url()).pathname)) executions++; });
  await page.goto(`http://127.0.0.1:${webPort}/app/demos`);
  await page.getByRole('heading', { name: 'Approved pipeline scenarios' }).waitFor();
  await page.getByText('Execution mode: mock.', { exact: false }).waitFor();
  assert.equal(await page.locator('.preset-card-full').count(), 20); checks++;
  assert.equal(await page.getByRole('button', { name: 'Switch to admin', exact: true }).count(), 0); checks++;
  await page.getByRole('button', { name: /^Output Inspection/ }).click();
  assert.equal(await page.locator('.preset-card-full').count(), 1); checks++;
  await page.getByRole('button', { name: /^All Features/ }).click();
  const search = page.getByRole('textbox', { name: 'Search scenarios' });
  await search.fill('preset-rag-denied');
  assert.equal(await page.locator('.preset-card-full').count(), 1); checks++;
  await page.locator('#preset-rag-denied .preset-run-btn').click();
  await page.locator('#preset-rag-denied .verification-status-banner').getByText('PASS', { exact: true }).waitFor();
  await page.getByText(/AUTHORIZATION_DENIED/).first().waitFor(); checks++;
  assert.equal(executions, 1); checks++;
  await search.fill('preset-contact-pii');
  assert.equal(await page.locator('#preset-contact-pii .preset-run-btn').isEnabled(), true); checks++;
  await page.locator('#preset-contact-pii .preset-run-btn').click();
  await page.locator('#preset-contact-pii .verification-status-banner').getByText('NOT IMPLEMENTED', { exact: true }).waitFor(); checks++;
  assert.equal(executions, 2); checks++;
  await page.getByRole('button', { name: 'Refresh readiness', exact: true }).click();
  await page.getByRole('button', { name: 'Refresh readiness', exact: true }).waitFor();
  assert.equal(await page.locator('#preset-contact-pii .verification-status-banner').innerText(), 'NOT IMPLEMENTED'); checks++;
  await page.locator('#preset-contact-pii .preset-chat-btn').click();
  await page.waitForURL('**/app/chat');
  const composer = page.locator('.composer textarea');
  await composer.waitFor();
  assert.match(await composer.inputValue(), /synthetic.customer@example.test/); checks++;
  assert.equal(executions, 2); checks++;
  await page.reload();
  await page.locator('.composer textarea').waitFor();
  assert.match(await page.locator('.composer textarea').inputValue(), /synthetic.customer@example.test/); checks++;
  assert.equal(executions, 2); checks++;
  assert.equal(await page.evaluate(() => sessionStorage.getItem('aegis-selected-preset')), null); checks++;
  const active = await page.request.get(`http://127.0.0.1:${apiPort}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  assert.equal((await active.json()).id, 'bob'); checks++;
  await page.goto(`http://127.0.0.1:${webPort}/app/demos`);
  await page.getByRole('button', { name: 'Next', exact: true }).click();
  await page.getByText('Guided tour · 2/', { exact: false }).waitFor(); checks++;
  await page.getByRole('button', { name: 'Prev', exact: true }).click();
  await page.getByText('Guided tour · 1/', { exact: false }).waitFor(); checks++;
  await page.setViewportSize({ width: 390, height: 844 });
  const overflow = await page.evaluate(() => ({ width: window.innerWidth, scroll: document.documentElement.scrollWidth, elements: [...document.querySelectorAll('*')].filter((element) => element.getBoundingClientRect().right > window.innerWidth + 1).slice(0, 15).map((element) => element.className) }));
  assert.equal(overflow.scroll <= overflow.width, true, JSON.stringify(overflow)); checks++;
  // Backend outage must be shown as an error, never a previous PASS.
  await page.route('**/api/demo/status', (route) => route.abort('connectionrefused'));
  await page.getByRole('button', { name: 'Refresh readiness', exact: true }).click();
  await page.getByRole('alert').getByText(/ERROR/).waitFor(); checks++;
  console.log(`${checks} browser integration assertions passed. Mock configured; no live inference asserted.`);
} finally {
  await browser?.close();
  backend.kill(); frontend.kill();
  await new Promise((resolve) => setTimeout(resolve, 500));
  // Only files created in the uniquely allocated test directory are removed.
  for (const name of ['synthetic.db', 'synthetic.db-journal', 'synthetic.db-wal', 'synthetic.db-shm']) await unlink(join(temp, name)).catch(() => {});
  await rmdir(temp).catch(() => {});
}
