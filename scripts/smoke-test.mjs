// End-to-end smoke test: open the built single-file page in headless Chromium and
// check that the official timetable data renders and the filters work.
// Usage: npm run build && node scripts/smoke-test.mjs [dist/index.html]
import {chromium} from 'playwright';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {readFileSync} from 'node:fs';

const file = resolve(process.argv[2] || 'dist/index.html');
const coverage = JSON.parse(readFileSync(new URL('../src/assets/coverage.json', import.meta.url)));
const browser = await chromium.launch({headless: true, executablePath: process.env.CHROMIUM_PATH || undefined});
const page = await browser.newPage({viewport: {width: 1400, height: 1000}});
const errors = [];
page.on('pageerror', e => errors.push(String(e)));
page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });

const stats = async () => {
  const cells = await page.locator('.hna-map-stats span').allInnerTexts();
  const num = i => Number((cells[i].match(/[\d,]+/) || ['0'])[0].replace(/,/g, ''));
  return {records: num(0), routes: num(1), airports: num(2), exclusive: num(3), status: cells[4]};
};
const fail = msg => { console.error('SMOKE FAIL:', msg); process.exitCode = 1; };

try {
  await page.goto(pathToFileURL(file).href, {waitUntil: 'load'});
  await page.waitForSelector('.hna-map-stats', {timeout: 30000});
  const today = await stats();
  console.log('default view (today, 2666 window):', JSON.stringify(today));
  if (!(today.records > 0 && today.routes > 0)) fail('no records rendered for the default date');

  // the full timetable, all time windows: must match coverage.json
  await page.getByRole('button', {name: '查看已收录计划'}).click();
  await page.locator('select').filter({has: page.locator('option', {hasText: '全部已收录时段'})}).first().selectOption('all').catch(() => {});
  const all = await stats();
  console.log('all timetable rows, all windows:', JSON.stringify(all));
  if (all.records !== coverage.timetable_rows) fail(`expected ${coverage.timetable_rows} timetable rows, page shows ${all.records}`);

  // table rows and a detail panel
  const firstRow = page.locator('table tbody tr').first();
  await firstRow.waitFor({timeout: 10000});
  await firstRow.click();
  await page.waitForSelector('.hna-detail', {timeout: 10000});
  const detail = await page.locator('.hna-detail').innerText();
  if (!/官网航班时刻表原文/.test(detail)) fail('detail panel does not show the official source note');

  // the 2025 archive source
  await page.locator('select').filter({has: page.locator('option', {hasText: '2025 官方全国参考表'})}).first().selectOption('official-2025');
  const archive = await stats();
  console.log('2025 archive:', JSON.stringify(archive));
  if (archive.records !== coverage.archive_rows) fail(`expected ${coverage.archive_rows} archive rows, page shows ${archive.records}`);
} catch (e) {
  fail(e.message);
} finally {
  if (errors.length) fail('browser errors: ' + errors.join(' | '));
  await browser.close();
}
if (!process.exitCode) console.log('SMOKE OK');
