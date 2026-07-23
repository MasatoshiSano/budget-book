# -*- coding: utf-8 -*-
import re, json, glob, os
import pdfplumber

FILES = {
    'd55d3237-statement_202601.pdf': '1月',
    'fc345a1d-statement_202602.pdf': '2月',
    '83a6f8b8-statement_202603.pdf': '3月',
    '833cca2e-statement_202604.pdf': '4月',
    '34ab9cea-statement_202605.pdf': '5月',
    '5011ddf6-statement_202606.pdf': '6月',
    '8a76ea80-statement_202607.pdf': '7月',
}
DIR = '/root/.claude/uploads/02b55f01-b334-5b26-9fc8-6e95ce3af906'

line_re = re.compile(r'^(\d{4}/\d{2}/\d{2})\s+(.+?)\s+(本人\*|ETC\*|家族\*)\s+(\S+払い)\s+(.+)$')

results = []
for fname, label in FILES.items():
    path = os.path.join(DIR, fname)
    with pdfplumber.open(path) as pdf:
        text = ''
        for page in pdf.pages:
            text += (page.extract_text() or '') + '\n'
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    req_m = re.search(r'ご請求金額[^0-9]*\n?([\d,]+)円', text) or re.search(r'(\d{4})年(\d{2})月ご請求金額.*?\n([\d,]+)円', text, re.S)
    header_m = re.search(r'(\d{4})年(\d{2})月ご請求金額', text)
    amt_line = None
    # header amount is the number immediately followed by 円 right after the "ご請求金額" line
    idx = next(i for i, l in enumerate(lines) if 'ご請求金額' in l and '年' in l)
    amt_line_text = lines[idx + 1]
    header_amt_m = re.match(r'([\d,]+)円', amt_line_text)
    header_total = int(header_amt_m.group(1).replace(',', '')) if header_amt_m else None

    pay_date_m = re.search(r'お支払日.*?\n(\d{4}/\d{2}/\d{2})', text)

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
    results.append({
        'file': fname,
        'label': label,
        'header_total': header_total,
        'parsed_sum': parsed_sum,
        'match': parsed_sum == header_total,
        'n_txns': len(txns),
        'unmatched': unmatched,
        'txns': txns,
    })

for r in results:
    print(r['file'], r['label'], 'header_total=', r['header_total'], 'parsed_sum=', r['parsed_sum'], 'match=', r['match'], 'n=', r['n_txns'])
    if r['unmatched']:
        print('  unmatched (continuation lines, expected):', r['unmatched'])

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/rakuten_parsed.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
