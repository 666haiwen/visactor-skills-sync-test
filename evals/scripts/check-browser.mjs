import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright';
import { withRequiredChecks } from './browser-checks.mjs';
import { useLocalAssets } from './local-browser-assets.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const directory = path.resolve(process.argv[2] || '');
const metadata = JSON.parse(await fs.readFile(path.join(directory, 'metadata.json'), 'utf8'));
const expected = await fs.readFile(path.join(directory, 'expectations.json'), 'utf8').then(JSON.parse).catch(async error => {
  if (error.code === 'ENOENT') {
    const expectations = JSON.parse(await fs.readFile(path.join(root, 'evals/cases', metadata.task.skill, 'expectations.json'), 'utf8'));
    return expectations[metadata.task.id];
  }
  throw error;
});
const outputs = path.join(directory, 'workspace/outputs');
const checks = [];
const errors = [];
const checkErrors = [];
const requests = [];
let browser;
let assetFailures = [];
const server = http.createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const target = path.resolve(outputs, '.' + pathname);
    if (!target.startsWith(outputs + path.sep)) { res.writeHead(403); res.end(); return; }
    const real = await fs.realpath(target);
    if (!real.startsWith((await fs.realpath(outputs)) + path.sep)) { res.writeHead(403); res.end(); return; }
    res.setHeader('Content-Type', ({'.html':'text/html; charset=utf-8','.js':'text/javascript','.json':'application/json','.css':'text/css'})[path.extname(real)] || 'application/octet-stream');
    res.end(await fs.readFile(real));
  } catch { res.writeHead(404); res.end(); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));

async function checkDeckNavigation(page, name, label, evidenceName) {
  let result;
  try {
    await page.waitForFunction(expectedLabel => {
      const slide = document.querySelector('.deck-slide.is-active');
      if (!slide || slide.dataset.slideLabel !== expectedLabel) return false;
      const rect = slide.getBoundingClientRect();
      const content = [...slide.querySelectorAll('.headline, .chart-frame')];
      return Math.abs(rect.x) < 1 && Math.abs(rect.y) < 1 && content.length > 0 &&
        content.every(node => Number(getComputedStyle(node).opacity) > 0.99);
    }, label, {timeout: 15000, polling: 100});
    result = {name, passed: true};
  } catch (error) {
    result = {name, passed: false, reason: String(error)};
  }
  checks.push(result);
  if (result.passed) {
    await page.screenshot({path: path.join(directory, `${evidenceName}.png`)});
    return true;
  } else {
    checkErrors.push({check: name, error: result.reason});
    const state = await page.evaluate(() => {
      const shell = document.querySelector('[data-deck-shell]');
      const track = document.querySelector('[data-deck-track]');
      return {
        activeLabel: document.querySelector('.deck-slide.is-active')?.dataset.slideLabel,
        index: shell?.style.getPropertyValue('--deck-index'),
        transform: track && getComputedStyle(track).transform,
        slides: [...document.querySelectorAll('.deck-slide')].map(slide => ({
          label: slide.dataset.slideLabel,
          rect: slide.getBoundingClientRect().toJSON(),
          headlineOpacity: slide.querySelector('.headline') && getComputedStyle(slide.querySelector('.headline')).opacity,
        })),
        scrollX, scrollY,
      };
    });
    await fs.writeFile(path.join(directory, `${evidenceName}-state.json`), JSON.stringify(state, null, 2) + '\n');
    await page.screenshot({path: path.join(directory, `${evidenceName}-failed.png`)});
    return false;
  }
}

try {
  browser = await chromium.launch({ channel: 'chromium', headless: true });
  const page = await browser.newPage({
    viewport: {width: 1440, height: 1000},
    ...(metadata.runner === 'fixed-browser-smoke' ? {reducedMotion: 'reduce'} : {}),
  });
  if (process.argv.includes('--local-assets')) {
    assetFailures = await useLocalAssets(page, `http://127.0.0.1:${server.address().port}`, path.join(root, 'evals'));
  }
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => requests.push({url:request.url(),error:request.failure()?.errorText}));
  page.on('response', response => { if (response.status() >= 400) requests.push({url:response.url(),status:response.status()}); });
  // Observe the instance produced by the installed template, without changing its options or data.
  await page.addInitScript(() => {
    window.__storyBuilds = [];
    window.__VSEED_AFTER_BUILD_SPEC__ = payload => window.__storyBuilds.push(payload);
  });
  await page.goto(`http://127.0.0.1:${server.address().port}/${expected.html}`, {waitUntil:'networkidle',timeout:60000});
  await page.waitForFunction(() => [...document.querySelectorAll('canvas')].some(c => c.width > 0 && c.height > 0), null, {timeout:15000});
  if (expected.engine === 'story') {
    await page.waitForFunction(() => {
      const charts = [...document.querySelectorAll('[data-chart-id]')];
      return charts.length > 0 && charts.every(c => c.querySelector('canvas'));
    }, null, {timeout:15000});
    const builds = await page.evaluate(() => JSON.parse(JSON.stringify(window.__storyBuilds, (key, value) => typeof value === 'function' ? '[function]' : value)));
    await fs.writeFile(path.join(directory, 'runtime-spec.json'), JSON.stringify(builds, null, 2) + '\n');
    checks.push({name:'storyChartsCompiled',passed:builds.length > 0});
    if (expected.deck) {
      const slides = page.locator('.deck-slide');
      checks.push({name:'deckSlides',passed:await slides.count() >= 2});
      const before = await page.locator('.deck-slide.is-active').getAttribute('data-slide-label');
      const next = await slides.nth(1).getAttribute('data-slide-label');
      await page.keyboard.press('ArrowRight');
      if (await checkDeckNavigation(page, 'deckNavigation', next, 'deck-next')) {
        await page.keyboard.press('ArrowLeft');
        await checkDeckNavigation(page, 'deckReturnNavigation', before, 'deck-return');
      }
    }
  }
  await page.screenshot({path:path.join(directory,'screenshot.png'),fullPage:true});
  const rendering = await page.evaluate(story => {
    const canvas = [...document.querySelectorAll(story ? '.chart-container canvas' : 'canvas')].find(c => c.width > 100 && c.height > 100);
    if (!canvas) return {passed:false,reason:'No chart/table canvas'};
    try {
      const pixels = canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
      let colored = 0;
      for(let i=0;i<pixels.length;i+=40) if(pixels[i+3]>0 && Math.min(pixels[i],pixels[i+1],pixels[i+2])<245) colored++;
      return {passed:colored>20,coloredSamples:colored};
    } catch(error) {return {passed:false,reason:String(error)};}
  }, expected.engine === 'story');
  checks.push({name:'nonBlankCanvas',...rendering});
} catch(error) {
  const reason = String(error);
  checks.push({name:'browserExecution',passed:false,reason});
  checkErrors.push({check:'browserExecution',error:reason});
} finally {
  if(browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
checks.push({name:'pageErrors',passed:errors.length===0},{name:'networkErrors',passed:requests.length===0});
if (process.argv.includes('--local-assets')) checks.push({name:'localAssets',passed:assetFailures.length===0});
const allChecks = withRequiredChecks(checks, expected.requiredChecks);
const result = {status:allChecks.every(check=>check.passed)?'passed':'failed',checks:allChecks,errors,checkErrors,requests,assetFailures,visualReview:'not-run'};
await fs.writeFile(path.join(directory,'browser.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
process.exitCode=result.status==='passed'?0:1;
