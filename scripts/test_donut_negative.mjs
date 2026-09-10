// Regression: the category donut must not use a net-of-refunds total as the
// percentage / arc-length base. Positive slices are the only ones drawn, so
// the denominator has to be their sum — otherwise a month with large refunds
// (Aug 2026 + 旅行・宿泊) tries to paint well past 360°.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { strict as assert } from 'node:assert';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');

const TOP_CATEGORIES = [
  '旅行・宿泊', '住居費', '交通費', '通信費・サブスク', '外食・カフェ', '保険',
  '食費（スーパー・コンビニ）', 'ショッピングモール・百貨店', '水道光熱費',
  '投資・貯蓄', 'ネットショッピング', '日用品・インテリア',
];
const PAYPAY_CONBINI_NAMES = new Set(['セブンーイレブン', 'ファミリーマート', 'ローソン']);

const TRANSACTIONS = JSON.parse(readFileSync(join(ROOT, 'data/unified_transactions.json'), 'utf8'));

function sliceAmounts(payMonth, { includeTravel, includeHousing, includeTransport }) {
  const rows = TRANSACTIONS.filter(t => {
    if (t.pay_month !== payMonth) return false;
    if (!includeTravel && t.category === '旅行・宿泊') return false;
    if (!includeHousing && t.category === '住居費') return false;
    if (!includeTransport && t.category === '交通費') return false;
    if (t.card === 'PayPayカード' && PAYPAY_CONBINI_NAMES.has(t.name)) return false;
    return true;
  });
  const totalsByCat = {};
  rows.forEach(t => { totalsByCat[t.category] = (totalsByCat[t.category] || 0) + t.amount; });
  const slices = TOP_CATEGORIES.map(cat => totalsByCat[cat] || 0);
  const otherAmt = Object.keys(totalsByCat).filter(c => !TOP_CATEGORIES.includes(c))
    .reduce((s, c) => s + totalsByCat[c], 0);
  if (otherAmt !== 0) slices.push(otherAmt);
  return slices;
}

const augustTravelOn = sliceAmounts('2026-08', {
  includeTravel: true, includeHousing: false, includeTransport: false,
});
const net = augustTravelOn.reduce((s, a) => s + a, 0);
const positive = augustTravelOn.filter(a => a > 0).reduce((s, a) => s + a, 0);
assert.ok(net > 0 && positive > net, `expected August+travel positive ${positive} > net ${net}`);
const buggySweep = positive / net * 360;
assert.ok(buggySweep > 360, `pre-fix donut would sweep ${buggySweep.toFixed(0)}° (got net ${net}, positive ${positive})`);
assert.equal(Math.round(positive / positive * 360), 360);

const template = readFileSync(join(ROOT, 'site/template.html'), 'utf8');
const index = readFileSync(join(ROOT, 'site/index.html'), 'utf8');
for (const [label, src] of [['template', template], ['index', index]]) {
  const donut = src.match(/function renderDonut\(\) \{[\s\S]*?\n\}/);
  assert.ok(donut, `${label}: renderDonut not found`);
  assert.match(
    donut[0],
    /const nonZero = shown\.filter\(s => s\.amt > 0\)[\s\S]*?const total = nonZero\.reduce/,
    `${label}: donut total must be the sum of positive slices, not the net of shown`,
  );
  assert.doesNotMatch(
    donut[0],
    /const total = shown\.reduce/,
    `${label}: donut must not use shown (net, including refunds) as the percentage base`,
  );
}

console.log('ok: donut percentage base is positive slices only');
console.log(`  2026-08 +travel net ¥${net.toLocaleString('ja-JP')} vs positive ¥${positive.toLocaleString('ja-JP')} (buggy would sweep ${buggySweep.toFixed(0)}°)`);
