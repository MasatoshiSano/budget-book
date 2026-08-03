# -*- coding: utf-8 -*-
# Merges the three per-card transaction files into data/unified_transactions.json,
# mapping each card's own category taxonomy onto one shared set of categories.
# Run after re-running parse_sumitomo.py / parse_categorize_paypay.py / parse_rakuten.py
# (+ categorize_sumitomo.py / categorize_rakuten.py) on newly uploaded statements.
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')

with open(os.path.join(DATA, 'sumitomo_transactions.json'), encoding='utf-8') as f:
    sumitomo = json.load(f)
with open(os.path.join(DATA, 'paypay_transactions.json'), encoding='utf-8') as f:
    paypay = json.load(f)
with open(os.path.join(DATA, 'rakuten_transactions.json'), encoding='utf-8') as f:
    rakuten = json.load(f)
bank_path = os.path.join(DATA, 'bank_transactions.json')
bank = json.load(open(bank_path, encoding='utf-8')) if os.path.exists(bank_path) else []
yucho_path = os.path.join(DATA, 'yucho_transactions.json')
yucho = json.load(open(yucho_path, encoding='utf-8')) if os.path.exists(yucho_path) else []
aeon_path = os.path.join(DATA, 'aeon_transactions.json')
aeon = json.load(open(aeon_path, encoding='utf-8')) if os.path.exists(aeon_path) else []

# Once an AEON card statement has been itemized (scripts/parse_aeon.py), the matching
# lump-sum "イオンフィナンシャルサービス" bank-debit guess for that pay_month is redundant
# and would double-count the same spend. Drop those months from the bank feed.
AEON_ITEMIZED_MONTHS = {r['pay_month'] for r in aeon}

# unify category taxonomy across the three cards
SUMITOMO_MAP = {
    '水道光熱費': '水道光熱費', '保険': '保険', '通信費・サブスク': '通信費・サブスク',
    'コンビニ': '食費（スーパー・コンビニ）', 'スーパー・食料品': '食費（スーパー・コンビニ）',
    'ドラッグストア': 'ドラッグストア', '外食・カフェ': '外食・カフェ',
    'ショッピングモール・百貨店': 'ショッピングモール・百貨店', '日用品・インテリア': '日用品・インテリア',
    'ファッション・美容': 'ファッション・美容', 'ネットショッピング': 'ネットショッピング',
    '交通費': '交通費', '旅行・宿泊（予約サイト）': '旅行・宿泊', 'レジャー・娯楽': 'レジャー・娯楽',
    'ふるさと納税': 'ふるさと納税', '手数料・利息': '手数料・利息', 'その他': 'その他',
}
PAYPAY_MAP = {
    '通信費・サブスク': '通信費・サブスク', 'コンビニ': '食費（スーパー・コンビニ）',
    'スーパー・食料品': '食費（スーパー・コンビニ）', 'ドラッグストア': 'ドラッグストア',
    '外食・カフェ': '外食・カフェ', 'ショッピングモール・百貨店': 'ショッピングモール・百貨店',
    '日用品・インテリア': '日用品・インテリア', 'ファッション・美容': 'ファッション・美容',
    '美容・健康': '美容・健康', '交通費': '交通費', '旅行・宿泊': '旅行・宿泊',
    '教育・資格': '教育・資格', 'その他': 'その他',
}
RAKUTEN_MAP = {
    '投資': '投資・貯蓄', '電子マネー・チャージ': '電子マネー・チャージ',
    '通信費・サブスク': '通信費・サブスク', '交通費': '交通費',
    'ネットショッピング': 'ネットショッピング', 'スーパー・食料品': '食費（スーパー・コンビニ）',
    'その他': 'その他',
}

# pay_month is stored as a sortable "YYYY-MM" key (not a bare "N月" label) so the
# site can derive however many month chips/groups it needs straight from the data,
# instead of a hardcoded month list that has to be hand-edited every statement cycle.
# Sumitomo/PayPay rows carry an exact pay_date already; Rakuten doesn't, so it's
# reconstructed here from the known 2026 statement dates (see scripts/parse_rakuten.py).
RAKUTEN_PAY_DATES = {
    '1月': '2026-01-27', '2月': '2026-02-27', '3月': '2026-03-27', '4月': '2026-04-27',
    '5月': '2026-05-27', '6月': '2026-06-29', '7月': '2026-07-27',
}

def pay_month_key(pay_date_str):
    # accepts 'YYYY-MM-DD' or 'YYYY/M/D' (PayPay's dates aren't zero-padded)
    y, m, _ = pay_date_str.replace('/', '-').split('-')
    return f'{y}-{int(m):02d}'

# 三井住友カードのMCCベースの自動分類は、海外の飲食店・交通・レジャー店舗を
# 「外食・カフェ」「交通費」「レジャー・娯楽」などにMCC通りに割り振ってしまい、
# 旅行として扱われない（2026年6月28〜30日のイタリア旅行で発覚：Rome/Napoli/Capri/
# Anacapriの現地決済31件、計127,336円が旅行・宿泊カテゴリから漏れていた）。
# 海外通貨建て（メモにEURなど）・「海外」を含む手数料・海外現地店舗名（英字＋
# 括弧書きの都市名）のいずれかに該当する行は、MCC上のカテゴリに関わらず旅行・宿泊
# として扱う。
import re
OVERSEAS_NAME_RE = re.compile(r"^[A-Z0-9'\.\*\- ]+\([A-Za-z\.\-/ ]+\)$")
def is_overseas_spend(memo, name):
    memo = memo or ''
    return ('EUR' in memo) or ('海外' in name) or ('海外' in memo) or bool(OVERSEAS_NAME_RE.match(name.strip()))

unified = []
for r in sumitomo:
    category = SUMITOMO_MAP.get(r['category'], 'その他')
    if is_overseas_spend(r.get('memo', ''), r['name']):
        category = '旅行・宿泊'
    unified.append({
        'date': r['use_date'], 'name': r['name'], 'amount': r['amount'],
        'card': '三井住友カード', 'pay_month': pay_month_key(r['pay_date']),
        'category': category,
    })
for r in paypay:
    unified.append({
        'date': r['use_date'].replace('/', '-'), 'name': r['name'], 'amount': r['amount'],
        'card': 'PayPayカード', 'pay_month': pay_month_key(r['pay_date']),
        'category': PAYPAY_MAP.get(r['category'], 'その他'),
    })
for r in rakuten:
    unified.append({
        'date': r['use_date'].replace('/', '-'), 'name': r['name'], 'amount': r['amount'],
        'card': '楽天カード', 'pay_month': pay_month_key(RAKUTEN_PAY_DATES[r['pay_month_label']]),
        'category': RAKUTEN_MAP.get(r['category'], 'その他'),
    })
# Bank items already de-duplicated against the 3 cards in scripts/parse_bank.py
# (card-payment debits, income, and interpersonal transfers are excluded there).
# イオンフィナンシャルサービス debits for months now itemized via the AEON card
# statement itself (see AEON_ITEMIZED_MONTHS above) are skipped here to avoid
# double-counting the same spend twice.
for r in bank:
    if 'イオンフィナンシャルサービス' in r['name'] and r['pay_month'] in AEON_ITEMIZED_MONTHS:
        continue
    unified.append({
        'date': r['date'], 'name': r['name'], 'amount': r['amount'],
        'card': '銀行引落', 'pay_month': r['pay_month'],
        'category': r['category'],
    })
# Yucho items already de-duplicated against the cards in scripts/parse_yucho.py
# (salary/bonus, the SBI-funding transfer, and card-payment debits are excluded there).
for r in yucho:
    unified.append({
        'date': r['date'], 'name': r['name'], 'amount': r['amount'],
        'card': 'ゆうちょ引落', 'pay_month': r['pay_month'],
        'category': r['category'],
    })
# AEON card items are itemized directly by scripts/parse_aeon.py (already in the
# final unified category taxonomy), so no per-source category map is needed here.
for r in aeon:
    unified.append({
        'date': r['date'], 'name': r['name'], 'amount': r['amount'],
        'card': 'イオンカード', 'pay_month': r['pay_month'],
        'category': r['category'],
    })

# sanity checks
from collections import Counter, defaultdict
print('total txns:', len(unified))
print('total amount:', sum(t['amount'] for t in unified))
by_card = defaultdict(int)
for t in unified:
    by_card[t['card']] += t['amount']
print('by card:', dict(by_card))

cats = Counter(t['category'] for t in unified)
print('categories:', len(cats))
for c, n in cats.most_common():
    print(' ', c, n)

with open(os.path.join(DATA, 'unified_transactions.json'), 'w', encoding='utf-8') as f:
    json.dump(unified, f, ensure_ascii=False, indent=2)
