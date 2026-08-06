# -*- coding: utf-8 -*-
# Parses 楽天カード statement PDFs (data/raw/rakuten/*.pdf) into
# data/rakuten_transactions.json. To add a new month: save the new statement
# PDF into data/raw/rakuten/ (any filename) and re-run this script — pay_month
# is read from each PDF's own "お支払日" line, not from the filename.
import re, json, glob, os, unicodedata

import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = sorted(glob.glob(os.path.join(ROOT, 'data', 'raw', 'rakuten', '*.pdf')))

line_re = re.compile(r'^(\d{4}/\d{2}/\d{2})\s+(.+?)\s+(本人\*|ETC\*|家族\*)\s+(\S+払い)\s+(.+)$')

def norm(s):
    return unicodedata.normalize('NFKC', s)

RULES = [
    ('投資', ['楽天証券投信積立']),
    ('電子マネー・チャージ', ['楽天キャッシュ チャージ']),
    ('通信費・サブスク', ['ﾈｯﾄﾌﾘｯｸｽ', 'ＮＥＴＦＬＩＸ', 'お名前．ｃｏｍ', 'ｵﾅﾏｴﾄﾞﾂﾄｺﾑ', 'ＧＯＯＧＬＥ＊ＣＬＯＵＤ', 'ＵＱ ｍｏｂｉｌｅ',
                      '楽天モバイル', 'ＣＵＲＳＯＲ']),
    ('交通費', ['ＥＴＣカード売上', 'ｺｽﾓｾｷﾕﾏｰｹﾃｲﾝｸﾞ']),
    ('ネットショッピング', ['ＡＭＡＺＯＮ．ＣＯ．ＪＰ', 'AMAZON.CO.JP']),
    ('スーパー・食料品', ['ｶﾝｻｲｽ-ﾊﾟ-', 'ﾗｲﾌｼﾕｸｶﾞﾜﾃﾝ']),
]

def categorize(name):
    hay = norm(name)
    for cat, kws in RULES:
        for kw in kws:
            if norm(kw) in hay:
                return cat
    return 'その他'

statements = []
for path in FILES:
    fname = os.path.basename(path)
    with pdfplumber.open(path) as pdf:
        text = ''
        for page in pdf.pages:
            text += (page.extract_text() or '') + '\n'
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    idx = next(i for i, l in enumerate(lines) if 'ご請求金額' in l and '年' in l)
    amt_line_text = lines[idx + 1]
    header_amt_m = re.match(r'([\d,]+)円', amt_line_text)
    header_total = int(header_amt_m.group(1).replace(',', '')) if header_amt_m else None

    pay_date_m = re.search(r'お支払日.*?\n(\d{4}/\d{2}/\d{2})', text)
    pay_date = pay_date_m.group(1).replace('/', '-') if pay_date_m else None

    txns = []
    unmatched = []
    in_table = False
    for l in lines:
        if l.startswith('利用日 利用店名'):
            in_table = True
            continue
        if not in_table:
            continue
        if l.startswith('※'):
            in_table = False
            continue
        m = line_re.match(l)
        if m:
            date, name, user, method, rest = m.groups()
            nums = re.findall(r'-?[\d,]+', rest)
            nums = [int(n.replace(',', '')) for n in nums]
            amount = nums[0]  # 利用金額
            txns.append({'date': date, 'name': name.strip(), 'user': user, 'method': method, 'amount': amount})
        else:
            unmatched.append(l)

    parsed_sum = sum(t['amount'] for t in txns)
    statements.append({
        'file': fname, 'pay_date': pay_date, 'header_total': header_total,
        'parsed_sum': parsed_sum, 'match': parsed_sum == header_total,
        'n_txns': len(txns), 'unmatched': unmatched, 'txns': txns,
    })

rows = []
for s in statements:
    pay_month_label = f'{int(s["pay_date"].split("-")[1])}月' if s['pay_date'] else None
    for t in s['txns']:
        rows.append({
            'use_date': t['date'],
            'name': t['name'],
            'user': t['user'],
            'method': t['method'],
            'amount': t['amount'],
            'pay_date': s['pay_date'],
            'pay_month_label': pay_month_label,
            'category': categorize(t['name']),
        })

rows.sort(key=lambda r: (r['pay_date'], r['use_date']))

for s in statements:
    print(s['file'], s['pay_date'], 'header_total=', s['header_total'], 'parsed_sum=', s['parsed_sum'],
          'match=', s['match'], 'n=', s['n_txns'])
    if s['unmatched']:
        print('  unmatched (continuation lines, expected):', s['unmatched'])

from collections import Counter
cat_counts = Counter(r['category'] for r in rows)
print('\n=== category counts ===')
for c, n in cat_counts.most_common():
    print(c, n)
others = [r for r in rows if r['category'] == 'その他']
print('その他 rows:', others)
print('\nTOTAL rows:', len(rows), 'TOTAL amount:', sum(r['amount'] for r in rows))

with open(os.path.join(ROOT, 'data', 'rakuten_transactions.json'), 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
