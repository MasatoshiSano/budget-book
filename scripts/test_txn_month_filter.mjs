// Regression: the 明細 table must use the same お支払月 filter as the hero.
// Filtering by 利用日 instead hides nearly all of a billing month (Japanese
// cards bill the previous month's usage).
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { strict as assert } from 'node:assert';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const TRANSACTIONS = JSON.parse(readFileSync(join(ROOT, 'data/unified_transactions.json'), 'utf8'));
const MONTH_KEYS = [...new Set(TRANSACTIONS.map(t => t.pay_month))].sort();

function useMonthOf(t) {
  const [y, m] = t.date.replaceAll('/', '-').split('-');
  return `${y}-${String(Number(m)).padStart(2, '0')}`;
}

function payMonthTotal(payMonth) {
  return TRANSACTIONS.filter(t => t.pay_month === payMonth).reduce((s, t) => s + t.amount, 0);
}
function useMonthTotal(useMonth) {
  return TRANSACTIONS.filter(t => useMonthOf(t) === useMonth).reduce((s, t) => s + t.amount, 0);
}

const aprPay = payMonthTotal('2026-04');
const aprUse = useMonthTotal('2026-04');
assert.ok(aprPay > 0 && aprUse > 0, 'expected April pay/use totals');
// Concrete trigger: 4月のお支払月 is ~¥971k; April 利用日 is ~¥474k.
// A table filtered by use date therefore cannot reconcile the April bill.
assert.ok(
  Math.abs(aprPay - aprUse) > 400000,
  `April pay vs use should diverge by >¥400k (got pay=${aprPay} use=${aprUse})`,
);

const hiddenIfUseDate = TRANSACTIONS.filter(t => t.pay_month === '2026-04' && useMonthOf(t) !== '2026-04');
assert.ok(
  hiddenIfUseDate.length / TRANSACTIONS.filter(t => t.pay_month === '2026-04').length > 0.8,
  'use-date filter would hide >80% of April-billed rows',
);

// 2025-11/12 usage is billed in 2026-01/02, so a pay_month 全期間 filter
// already includes those rows. The use-date special case was unnecessary.
const earlyUse = TRANSACTIONS.filter(t => {
  const um = useMonthOf(t);
  return um === '2025-11' || um === '2025-12';
});
assert.ok(earlyUse.length > 0, 'expected 2025-11/12 usage rows');
assert.ok(
  earlyUse.every(t => MONTH_KEYS.includes(t.pay_month)),
  'early use-date rows must have a pay_month inside MONTH_KEYS',
);

const template = readFileSync(join(ROOT, 'site/template.html'), 'utf8');
const index = readFileSync(join(ROOT, 'site/index.html'), 'utf8');
for (const [label, src] of [['template', template], ['index', index]]) {
  assert.ok(!src.includes('function filteredByUseDate'), `${label}: must not filter 明細 by use date`);
  const table = src.match(/function renderTable\(\) \{[\s\S]*?let rows = filtered\(\);/);
  assert.ok(table, `${label}: renderTable must use filtered() (pay_month)`);
}

console.log('ok: 明細 table stays on お支払月, matching the hero');
console.log(`  2026-04 pay ${aprPay.toLocaleString('ja-JP')} vs use ${aprUse.toLocaleString('ja-JP')} (buggy table would hide ${hiddenIfUseDate.length} billed rows)`);
