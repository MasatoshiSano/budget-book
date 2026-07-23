import re, json, glob, os
import pdfplumber

FILES = sorted(glob.glob('/root/.claude/uploads/02b55f01-b334-5b26-9fc8-6e95ce3af906/*.pdf'))

full_line_re = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+)\s+１\s+１\s+(-?[\d,]+)\s*(.*)$')
short_line_re = re.compile(r'^(\d{2}/\d{2}/\d{2})\s+(.+?)\s+(-?[\d,]+)$')
skip_patterns = [
    '備考の◎印は', '三井住友カード株式会社', '大阪市中央区', '登録番号', 'ページ',
    'お支払い総額', 'ご利用', 'ご利用日', '金額', '現地通貨額', 'お支払金額総合計',
    '利用枠', '海外キャッシュサービス', 'ご返済', '実質年率', 'ご利用分',
]

def is_skip(line):
    line = line.strip()
    if not line:
        return True
    for p in skip_patterns:
        if p in line:
            return True
    return False

results = []  # list of dict per statement
for f in FILES:
    base = os.path.basename(f)
    with pdfplumber.open(f) as pdf:
        text = ''
        for page in pdf.pages:
            t = page.extract_text() or ''
            text += t + '\n'
    lines = text.split('\n')

    # header info (PDF uses CJK-compatibility variants for 支/月/日, so use wildcards)
    pay_date_m = re.search(r'お.払い.\s*(\d{4})年(\d{1,2}).(\d{1,2}).', text)
    total_m = re.search(r'合計額\s*([\d,]+)\s*円', text)
    grand_total_m = re.search(r'総合計＞\s*([\d,]+)', text)

    pay_year, pay_month, pay_day = pay_date_m.groups() if pay_date_m else (None, None, None)
    header_total = int(total_m.group(1).replace(',', '')) if total_m else None
    grand_total = int(grand_total_m.group(1).replace(',', '')) if grand_total_m else None

    txns = []
    unmatched = []
    for line in lines:
        line = line.strip()
        if is_skip(line):
            continue
        m = full_line_re.match(line)
        if m:
            date, name, amt1, amt2, rest = m.groups()
            amt1 = int(amt1.replace(',', ''))
            txns.append({'date': date, 'name': name.strip(), 'amount': amt1, 'memo': rest.strip()})
            continue
        m2 = short_line_re.match(line)
        if m2:
            date, name, amt = m2.groups()
            amt = int(amt.replace(',', ''))
            txns.append({'date': date, 'name': name.strip(), 'amount': amt, 'memo': ''})
            continue
        unmatched.append(line)

    parsed_sum = sum(t['amount'] for t in txns)

    results.append({
        'file': base,
        'pay_date': f'{pay_year}-{int(pay_month):02d}-{int(pay_day):02d}' if pay_year else None,
        'header_total': header_total,
        'grand_total': grand_total,
        'parsed_sum': parsed_sum,
        'match': parsed_sum == grand_total,
        'n_txns': len(txns),
        'unmatched_lines': unmatched,
        'txns': txns,
    })

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/parsed.json', 'w', encoding='utf-8') as out:
    json.dump(results, out, ensure_ascii=False, indent=2)

for r in results:
    print(r['file'], r['pay_date'], 'header_total=', r['header_total'], 'grand_total=', r['grand_total'],
          'parsed_sum=', r['parsed_sum'], 'match=', r['match'], 'n=', r['n_txns'])
    if r['unmatched_lines']:
        print('  UNMATCHED:', r['unmatched_lines'])
