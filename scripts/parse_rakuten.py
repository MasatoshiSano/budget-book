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
# Header row looks like:
#   0ポイント -23,044円 26,950円
# (獲得ポイント, 調整額/キャンセル等, 返金額). 6月以降は列名が「キャンセル等」だが
# 数値の並びに変わりはない。
REFUND_LINE_RE = re.compile(r'ポイント\s+(-?[\d,]+)円\s+(-?[\d,]+)円')

def norm(s):
    return unicodedata.normalize('NFKC', s)

def parse_refund_yen(text):
    """明細書ヘッダーの返金額。取れなければ 0。"""
    m = REFUND_LINE_RE.search(text)
    if not m:
        return 0
    return int(m.group(2).replace(',', ''))

def statement_balance(header_total, parsed_sum, refund):
    """明細合計を「ご請求金額 − 返金額」（その月の実キャッシュ）に合わせる差分。

    楽天はキャンセルを明細行に出さず、ヘッダーの調整額・返金額にだけ載せる。
    2026年2月分はご請求金額 0円・調整額 -23,044円・返金額 26,950円で、
    明細 23,044円だけを拾うと、1月に計上した投信積立 49,994円のキャンセルが
    消えて支出が約5万円過大になる。
    """
    if header_total is None:
        return 0
    return header_total - parsed_sum - refund

def reversal_name(delta, prior_txns):
    """差分の符号を反転した金額が直前までの明細にあれば、その店名を流用する。"""
    if not delta:
        return '請求調整（キャンセル・返金）'
    target = -delta
    for t in reversed(prior_txns):
        if t['amount'] == target:
            return t['name'] + '（キャンセル・返金）'
    return '請求調整（キャンセル・返金）'

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

def parse_pdf_text(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    idx = next(i for i, l in enumerate(lines) if 'ご請求金額' in l and '年' in l)
    amt_line_text = lines[idx + 1]
    header_amt_m = re.match(r'([\d,]+)円', amt_line_text)
    header_total = int(header_amt_m.group(1).replace(',', '')) if header_amt_m else None

    pay_date_m = re.search(r'お支払日.*?\n(\d{4}/\d{2}/\d{2})', text)
    pay_date = pay_date_m.group(1).replace('/', '-') if pay_date_m else None
    refund = parse_refund_yen(text)

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
    return {
        'pay_date': pay_date,
        'header_total': header_total,
        'refund': refund,
        'parsed_sum': parsed_sum,
        'unmatched': unmatched,
        'txns': txns,
    }

def apply_statement_balance(parsed, prior_txns):
    """ヘッダーの調整額・返金を1行足して、お支払月の合計を実キャッシュに合わせる。"""
    delta = statement_balance(parsed['header_total'], parsed['parsed_sum'], parsed['refund'])
    if not delta:
        parsed['match'] = parsed['parsed_sum'] == parsed['header_total']
        parsed['n_txns'] = len(parsed['txns'])
        return parsed
    pay_date_slash = parsed['pay_date'].replace('-', '/') if parsed['pay_date'] else ''
    parsed['txns'].append({
        'date': pay_date_slash,
        'name': reversal_name(delta, prior_txns),
        'user': '本人*',
        'method': '1回払い',
        'amount': delta,
    })
    parsed['parsed_sum'] = sum(t['amount'] for t in parsed['txns'])
    cash = parsed['header_total'] - parsed['refund'] if parsed['header_total'] is not None else None
    parsed['match'] = parsed['parsed_sum'] == cash
    parsed['n_txns'] = len(parsed['txns'])
    return parsed

def parse_statements(files=None):
    files = FILES if files is None else files
    statements = []
    prior_txns = []
    for path in files:
        fname = os.path.basename(path)
        with pdfplumber.open(path) as pdf:
            text = ''
            for page in pdf.pages:
                text += (page.extract_text() or '') + '\n'
        parsed = parse_pdf_text(text)
        apply_statement_balance(parsed, prior_txns)
        parsed['file'] = fname
        statements.append(parsed)
        prior_txns.extend(parsed['txns'])
    return statements

def statements_to_rows(statements):
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
    return rows

def main():
    from collections import Counter
    statements = parse_statements()
    rows = statements_to_rows(statements)

    for s in statements:
        cash = s['header_total'] - s['refund'] if s['header_total'] is not None else None
        print(s['file'], s['pay_date'], 'header_total=', s['header_total'],
              'refund=', s['refund'], 'parsed_sum=', s['parsed_sum'],
              'cash=', cash, 'match=', s['match'], 'n=', s['n_txns'])
        if s['unmatched']:
            print('  unmatched (continuation lines, expected):', s['unmatched'])

    cat_counts = Counter(r['category'] for r in rows)
    print('\n=== category counts ===')
    for c, n in cat_counts.most_common():
        print(c, n)
    others = [r for r in rows if r['category'] == 'その他']
    print('その他 rows:', others)
    print('\nTOTAL rows:', len(rows), 'TOTAL amount:', sum(r['amount'] for r in rows))

    with open(os.path.join(ROOT, 'data', 'rakuten_transactions.json'), 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main()
