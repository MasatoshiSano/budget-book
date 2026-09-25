// Regression checks for overview totals: 前月比 and the monthly stacked chart
// must use the same content filter as the hero (passesContentFilter).
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { strict as assert } from 'node:assert';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

const PAYPAY_CONBINI_NAMES = new Set(['セブンーイレブン', 'ファミリーマート', 'ローソン']);
function isPaypayConbini(t) {
  return t.card === 'PayPayカード' && PAYPAY_CONBINI_NAMES.has(t.name);
}
function passesContentFilter(t, state) {
  if (!state.includeTravel && t.category === '旅行・宿泊') return false;
  if (!state.includeHousing && t.category === '住居費') return false;
  if (!state.includeTransport && t.category === '交通費') return false;
  if (isPaypayConbini(t)) return false;
  return true;
}

const TRANSACTIONS = JSON.parse(readFileSync(join(ROOT, 'data/unified_transactions.json'), 'utf8'));
const defaultState = { includeTravel: false, includeHousing: false, includeTransport: false };

function monthTotal(payMonth, state) {
  return TRANSACTIONS
    .filter(t => t.pay_month === payMonth && passesContentFilter(t, state))
    .reduce((s, t) => s + t.amount, 0);
}
function unfilteredMonthTotal(payMonth) {
  return TRANSACTIONS.filter(t => t.pay_month === payMonth).reduce((s, t) => s + t.amount, 0);
}

const apr = monthTotal('2026-04', defaultState);
const mar = monthTotal('2026-03', defaultState);
const marRaw = unfilteredMonthTotal('2026-03');
assert.ok(apr > 0 && mar > 0, 'expected April/March living-cost totals');
const realPct = (apr - mar) / mar * 100;
const buggyPct = (apr - marRaw) / marRaw * 100;
assert.ok(realPct > 0, `April living-cost MoM should be up, got ${realPct.toFixed(1)}%`);
assert.ok(buggyPct < 0, `pre-fix comparison (vs unfiltered March) should invert the sign, got ${buggyPct.toFixed(1)}%`);

const jun = monthTotal('2026-06', defaultState);
const may = monthTotal('2026-05', defaultState);
const mayRaw = unfilteredMonthTotal('2026-05');
assert.ok((jun - may) / may > 0, 'June living-cost MoM should be up');
assert.ok((jun - mayRaw) / mayRaw < 0, 'pre-fix June vs unfiltered May should invert the sign');

const template = readFileSync(join(ROOT, 'site/template.html'), 'utf8');
const index = readFileSync(join(ROOT, 'site/index.html'), 'utf8');
for (const [label, src] of [['template', template], ['index', index]]) {
  const prev = src.match(/const prevTotal = TRANSACTIONS\.filter\(t =>[^;]+passesContentFilter\(t\)/);
  assert.ok(prev, `${label}: prevTotal must apply passesContentFilter`);
  const trend = src.match(/function renderTrend\(\) \{[\s\S]*?const rows = TRANSACTIONS\.filter\(t =>[^;]+passesContentFilter\(t\)/);
  assert.ok(trend, `${label}: renderTrend must apply passesContentFilter`);
}

console.log('ok: overview filters keep 前月比 and trend aligned with the hero');
console.log(`  2026-04 living-cost MoM ${realPct.toFixed(1)}% (buggy would show ${buggyPct.toFixed(1)}%)`);
