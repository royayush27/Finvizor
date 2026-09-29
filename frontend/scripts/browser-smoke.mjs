// Dependency-free Chrome smoke test. Run after starting the API and frontend.
// CHROME_PATH can override the Windows Chrome installation path.
import { spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';

const output = path.resolve('../.artifacts');
await mkdir(output, { recursive: true });
const chrome = spawn(process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', [
  '--headless=new', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=9227',
  `--user-data-dir=${path.join(output, 'chrome-profile')}`, 'about:blank',
], { windowsHide: true, stdio: 'ignore' });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
let ws;
try {
  let target;
  for (let i = 0; i < 60; i++) {
    try { target = (await (await fetch('http://127.0.0.1:9227/json')).json()).find(t => t.type === 'page'); } catch {}
    if (target) break;
    await delay(500);
  }
  assert(target, 'Chrome debugger must start');
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(resolve => ws.addEventListener('open', resolve, { once: true }));
  let sequence = 0;
  const pending = new Map();
  const exceptions = [];
  ws.addEventListener('message', event => {
    const data = JSON.parse(event.data);
    if (data.method === 'Runtime.exceptionThrown') exceptions.push(data.params.exceptionDetails);
    if (data.id && pending.has(data.id)) {
      const { resolve, reject } = pending.get(data.id);
      pending.delete(data.id);
      data.error ? reject(new Error(JSON.stringify(data.error))) : resolve(data.result);
    }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async expression => {
    const result = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const until = async (expression, timeout = 20000) => {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) { if (await evaluate(expression)) return; await delay(500); }
    throw new Error(`Timed out: ${expression}\n${await evaluate('document.body.innerText')}`);
  };
  const click = text => evaluate(`Array.from(document.querySelectorAll('button,a')).find(el => el.textContent.trim() === ${JSON.stringify(text)})?.click()`);
  const screenshot = async name => {
    const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true });
    await writeFile(path.join(output, name), Buffer.from(data, 'base64'));
  };
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false });
  await send('Page.navigate', { url: 'http://127.0.0.1:3000' });
  await until('document.querySelector(".overview")');
  await evaluate('localStorage.clear()');
  await send('Page.reload');
  await until('document.querySelector(".overview")');
  await delay(1000);
  await screenshot('overview-desktop.png');
  await click('Build a portfolio ↗');
  await until('document.body.innerText.includes("Communication Services")');
  await evaluate(`Array.from(document.querySelectorAll('button')).find(el => el.textContent.includes('Technology'))?.click()`);
  await screenshot('sectors-desktop.png');
  await click('Continue to Risk Assessment →');
  await until('document.body.innerText.includes("Investment experience")');
  await click('Continue to Portfolio Builder →');
  await until('document.body.innerText.includes("Screened allocation")');
  await click('Choose your holdings');
  await click('AAPL');
  await click('MSFT');
  await click('Generate Portfolio →');
  await until('document.body.innerText.includes("Each selected stock needs a weight greater than zero.")');
  await evaluate(`document.querySelectorAll('main input[type="number"]').forEach(el => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(el, '50');
    el.dispatchEvent(new Event('input', { bubbles: true }));
  })`);
  await until('document.body.innerText.includes("Total: 100.0%")');
  await screenshot('allocation-desktop.png');
  await click('Generate Portfolio →');
  await until('JSON.parse(localStorage.getItem("finvizor-wizard-state"))?.state.activeJob?.job_id');
  await send('Page.reload');
  await until('document.body.innerText.includes("Your research report")', 180000);
  await until('document.querySelectorAll(".js-plotly-plot").length === 3');
  await delay(1500);
  assert(await evaluate('document.body.innerText.includes("Trailing return")'));
  assert(await evaluate('document.querySelectorAll("tbody tr").length === 2'));
  assert(await evaluate('document.body.innerText.includes("Est. shares")'));
  assert(await evaluate(`fetch(document.querySelector('a[href$="export.csv"]').href).then(r => r.text()).then(csv => csv.includes('Trailing Return %') && csv.includes('AAPL'))`));
  await screenshot('results-desktop.png');
  await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await delay(1000);
  assert(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Results must fit mobile width');
  await screenshot('results-mobile.png');
  await send('Page.navigate', { url: 'http://127.0.0.1:3000' });
  await until('document.querySelector(".overview")');
  await delay(1000);
  assert(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Overview must fit mobile width');
  await screenshot('overview-mobile.png');
  assert.equal(exceptions.length, 0, JSON.stringify(exceptions));
  console.log('PASS: desktop/mobile layout, sector loading, risk scoring, live manual generation, charts and report. Screenshots in .artifacts/.');
} finally {
  ws?.close();
  chrome.kill();
}
