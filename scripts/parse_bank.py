# -*- coding: utf-8 -*-
# Parses the 住信SBIネット銀行 代表口座 statement PDFs into data/bank_transactions.json.
# Only keeps rows that represent real household spending not already captured by
# the 3 card statements (rent, the AEON payments, the ATM cash withdrawals).
# Excluded on purpose:
#   - 口座振替/振込 ミツイスミトモカード: duplicates the Sumitomo card statements
#   - 定額自動入金: money moving IN to this account (income), not spending
#   - 振込＊サノ.../ことら送金 アサダサナエ.../振込＊セキスイハウス...: transfers between
#     the couple's own accounts or a deposit refund, not consumption
#   - 地方税/国税/利息: sub-¥30 bank bookkeeping entries, not material
import re
import json
import glob
import os
import pdfplumber

DIR = '/root/.claude/uploads/02b55f01-b334-5b26-9fc8-6e95ce3af906'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = sorted(glob.glob(os.path.join(DIR, '*download_*.pdf')))
line_re = re.compile(r'^(\d{4})年(\d{2})月(\d{2})日\s+(.+?)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)$')

# content substring -> (category, display name)
KEEP = [
    ('オリコ ヤチン', '住居費', '家賃（オリコ・旧居／〜2026年4月）'),
    ('イオンフィナンシャルサービス', '旅行・宿泊', 'イオンフィナンシャルサービス（海外旅行関連・本人推定）'),
    ('イオンフイナンシヤルサービス', '旅行・宿泊', 'イオンフィナンシャルサービス（海外旅行関連・本人推定）'),
    ('ミツビシジシヨハウスネツト', '住居費', '三菱地所ハウスネット（新居関連）'),
    ('ＡＴＭ', '現金（使途不明）', 'ATM引き出し'),
]

rows = []
for f in FILES:
    with pdfplumber.open(f) as pdf:
        text = pdf.pages[0].extract_text()
    for line in text.split('\n'):
        line = line.strip()
        m = line_re.match(line)
        if not m:
            continue
        y, mo, d, content, out_amt, in_amt, balance = m.groups()
        out_amt = int(out_amt.replace(',', ''))
        if out_amt <= 0:
            continue
        for needle, category, display_name in KEEP:
            if needle in content:
                rows.append({
                    'date': f'{y}-{mo}-{d}',
                    'name': display_name,
                    'amount': out_amt,
                    'category': category,
                    'pay_month': f'{y}-{mo}',
                })
                break

rows.sort(key=lambda r: r['date'])
print(f'kept {len(rows)} bank rows')
for r in rows:
    print(r['date'], r['category'], r['name'], f"{r['amount']:,}")
print('total:', f"{sum(r['amount'] for r in rows):,}")

with open(os.path.join(ROOT, 'data', 'bank_transactions.json'), 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
