# -*- coding: utf-8 -*-
# Parses ゆうちょ銀行 (Japan Post Bank) statement CSVs (data/raw/yucho/*.csv, cp932
# encoded) into data/yucho_transactions.json. To add a new month: save the new
# statement CSV into data/raw/yucho/ (any filename) and re-run this script.
# Rows are de-duplicated by 取引ID (transaction id) since ゆうちょ's exported CSVs
# cover a rolling date window and can overlap between consecutive downloads.
# This is the salary account, so most rows are excluded on purpose:
#   - 給与/賞与: salary/bonus, income not spending
#   - 自払 ｽﾐｼﾝＳＢＩネット: internal transfer funding the SBI household-bills account
#     (already visible there as "定額自動入金"; counting it here too would double it)
#   - 自払 PAYPAYカード / 楽天カードサービス: duplicates already itemized from the card
#     statements themselves (data/paypay_transactions.json, data/rakuten_transactions.json)
#   - 自払 アメックス: kept out until we have the actual Amex statement to itemize it;
#     dropping an unitemized lump sum in as "その他" would just hide real spending detail
import csv
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, 'data', 'raw', 'yucho')
FILES = sorted(glob.glob(os.path.join(RAW_DIR, '*.csv')))

# 詳細２ substring -> (category, display name)
KEEP = [
    ('全労済', '保険', '全労済（ゆうちょ引落）'),
]

seen_txn_ids = set()
rows = []
for path in FILES:
    with open(path, encoding='cp932', newline='') as f:
        lines = f.read().split('\n')
    header_idx = next(i for i, l in enumerate(lines) if l.startswith('取引日,'))
    reader = csv.reader(lines[header_idx:])
    header = next(reader)
    for row in reader:
        if len(row) < 6 or not row[0]:
            continue
        date, txn_id, in_amt, out_amt, detail1, detail2 = row[0], row[1], row[2], row[3], row[4], row[5]
        if not out_amt:
            continue  # only interested in outgoing (spending) rows
        if txn_id in seen_txn_ids:
            continue  # exported CSVs cover overlapping date windows; dedupe by 取引ID
        for needle, category, display_name in KEEP:
            if needle in detail2:
                rows.append({
                    'date': f'{date[0:4]}-{date[4:6]}-{date[6:8]}',
                    'name': display_name,
                    'amount': int(out_amt.replace(',', '')),
                    'category': category,
                    'pay_month': f'{date[0:4]}-{date[4:6]}',
                })
                seen_txn_ids.add(txn_id)
                break

rows.sort(key=lambda r: r['date'])
print(f'kept {len(rows)} yucho rows')
for r in rows:
    print(r['date'], r['category'], r['name'], f"{r['amount']:,}")

with open(os.path.join(ROOT, 'data', 'yucho_transactions.json'), 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
