# -*- coding: utf-8 -*-
# Parses 三井住友カード statement PDFs (data/raw/sumitomo/*.pdf) into
# data/sumitomo_transactions.json. To add a new month: save the new statement
# PDF into data/raw/sumitomo/ (any filename) and re-run this script — pay_month
# is read from each PDF's own "お支払い" header, not from the filename.
import re, json, glob, os, unicodedata
import pdfplumber

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILES = sorted(glob.glob(os.path.join(ROOT, 'data', 'raw', 'sumitomo', '*.pdf')))

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

# The source PDF renders some common kanji using CJK-Radical / Kangxi-Radical
# lookalike codepoints instead of the standard ideograph. NFKC fixes some
# (支->支, 日->日) but not all, so patch the rest by hand.
RADICAL_FIX = {
    '⻄': '西', '⻑': '長', '⻲': '亀', '⼀': '一', '⼒': '力',
    '⼗': '十', '⼝': '口', '⼟': '土', '⼤': '大', '⼦': '子',
    '⼩': '小', '⼭': '山', '⼾': '戸', '⼿': '手', '⽉': '月',
    '⽔': '水', '⽣': '生', '⽤': '用', '⽥': '田', '⽯': '石',
    '⾁': '肉', '⾞': '車', '⾦': '金', '⾹': '香',
}

def norm(s):
    s = ''.join(RADICAL_FIX.get(ch, ch) for ch in s)
    return unicodedata.normalize('NFKC', s)

# category rules: (category, [keywords]) checked in order, first match wins.
# All keywords are matched against NORMALIZED text (see norm()), so write
# keywords using standard kanji even though the source PDF uses radical lookalikes.
RULES = [
    ('水道光熱費', ['関西電力']),
    ('保険', ['ソニ－生命', 'ソニー生命', '生命保険']),
    ('通信費・サブスク', ['Ａｍａｚｏｎプライム', 'Amazonプライム', 'フェリカポケット', 'ＧＯアプリ', 'ＧＯ（タクシーアプリ', 'ＣＯＮＥ', 'Ｒｅｎｔｉｏ']),
    ('手数料・利息', ['回収事務手数料', '遅延損害', 'ＡＴＭ利用手数料', 'ATM利用手数料', '海外キャッシュサービス利息', '海外キャッシング', 'ＰＺＡ ＤＥＬＬＡ ＶＩＴＴＯＲＩＡ', 'PZA DELLA VITTORIA']),
    ('ふるさと納税', ['ふるさと納税']),
    ('旅行・宿泊（予約サイト）', ['Ｔｒｉｐ．ｃｏｍ', 'Trip.com', 'ａｇｏｄａ', 'agoda', '株式会社一休', 'ＯＭＩＯ', 'OMIO', 'ベルトラ']),
    ('コンビニ', ['セブン－イレブン', 'ファミリーマート', 'ローソン']),
    ('ドラッグストア', ['スギ薬局', 'ココカラファイン']),
    ('スーパー・食料品', ['ダイエー', 'イズミヤ', '阪急オアシス', 'いかり', 'ライフ夙川店', '関西スーパー', '業務ス', 'オーケー', '成城石井', 'イオンリテール', 'サニーサイド', 'ＳＵＮＮＹＳＩＤＥ', 'ＣＡＲＲＥＦＯＵＲ', 'CONAD', 'ＣＡＳＴＲＯＮＩ', 'CASTRONI']),
    ('日用品・インテリア', ['ダイソー', 'ホームセンターコーナン', 'ロイヤルホームセンター', 'ニトリ', '無印良品', 'ＩＫＥＡ', 'IKEA', 'ドン‧キホーテ', 'ドン・キホーテ']),
    ('ファッション・美容', ['ユニクロ', 'ノムラクリーニング']),
    ('ネットショッピング', ['ＡＭＡＺＯＮ．ＣＯ．ＪＰ', 'AMAZON.CO.JP', 'ヤマダデンキ']),
    ('交通費', ['タイムズ', 'ＥＮＥＯＳ', 'ENEOS', 'ＡＴＡＣ', 'ATAC', 'ＦＲＥＥＮＯＷ', 'FREENOW', 'ＳＮＡＶ', 'SNAV', 'ＳＴＡＩＡＮＯ', 'ＦＩＵＭＩＣＩＮＯ', 'FIUMICINO'
                 ]),
    ('外食・カフェ', [
        'マクドナルド', 'スシロー', 'リンガーハット', 'ぎょうざの店', 'ワンカルビ', '焼肉きんぐ',
        '廻鮮鮨', '上島珈琲店', '星乃珈琲店', 'スターバックス', 'ブーランジェリー', '菓子店',
        'ダイニー', '正家', 'サワダ飯店', 'パンカラト', 'カフェ', '珈琲', 'ＲＩＳＴＯＲＡＮＴＥ', 'RISTORANTE',
        'ＣＡＦＦＥ', 'CAFFE', 'ＰＯＭＰＩ', 'ＴＲＥＣＡＦＦＥ', 'ＬＡ ＣＡＳＡ ＤＥＬ ＣＡＦＦＥ',
        '一鶴', '一休', 'ぶたしょう', '動物王国', 'どうぶつ王国', 'ヒシミツ醤油', 'タカムラ',
        'キャトルエピス', 'ななや', 'ＧＲＥＥＮＩＴＹ', 'ダニエル本店', 'ＫＩＮＯＫＵＮＩＹＡ',
        'ＲＡＶＩＯＬＯ', 'ＦＬＯＲ', 'ＬＡＲＩＮＡＳＣＥＮＴＥ', 'ＮＩＮＯ', 'ＤＵＥ ＰＩＮＩ',
        'ＧＲＡＮ ＢＡＲ', 'ＤＡ ＲＯＭＥＯ', 'ＢＥＴＲＥＥ', 'ｙｏｕ ｄｏｎｕｔ',
        'ちひろ', '成城石井 梅田', 'サワダ', '鉄板焼き', 'お好み焼き', 'ちか店', 'エルベラン',
        'ＥＮＣＯＲＥ ＵＮ ＭＡＴＩＮ', 'サービスエリア', '三本松ぱん', 'Ｍａｓｈｉｓｓｏｙｏ',
        'Ｓｑｕａｒｅ', 'ＢＩＧ ＢＥＡＮＳ', 'ファレットフル', '放香堂', 'ＣＡＱＰＴＡＩＮ ＣＡＮＤＹ', 'CAQPTAIN CANDY',
    ]),
    ('レジャー・娯楽', ['ＭＯＶＩＸ', 'シネ‧リーブル', 'シネ・リーブル', '動物王国', 'どうぶつ王国', 'ＫＯＢＥニュ', '５４００６０４', 'ＣＯＮＳＯＲＺＩＯ', 'CONSORZIO', 'ＣＵＬＴＵＲＥ', 'CULTURE', 'ＣＯＯＰＥＲＡＴＩＶＡ', 'COOPERATIVA', 'ＢＡＴＴＥＬＬＩＥＲＩ', 'BATTELLIERI', 'ジュンク堂']),
    ('ショッピングモール・百貨店', ['阪急西宮ガーデンズ', '神戸阪急', '阪急百貨店', '阪急梅田',
                              'ららぽーと', 'ＫＩＴＴＥ', 'ルクア', 'ＵＭＩＥ', 'ｕｍｉｅ', '三井アウトレット',
                              'キューズモール', 'イオンモール', 'ミント神戸', 'ピオレ姫路', 'モンテメール',
                              '阪急三番街', 'ｅｋｉｍｏ', 'コクミン']),
]

# 海外決済の overseas-spend reclassification (旅行・宿泊への統一) は
# scripts/consolidate.py 側で全ソース共通のルールとして扱う。ここではMCC相当の
# 一次分類のみ行う。

def categorize(name, memo):
    hay = norm(name) + ' ' + norm(memo)
    for cat, kws in RULES:
        for kw in kws:
            if kw and norm(kw) in hay:
                return cat
    return 'その他'

statements = []
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
    grand_total_m = re.search(r'総合計＞\s*([\d,]+)', text)

    pay_year, pay_month, pay_day = pay_date_m.groups() if pay_date_m else (None, None, None)
    grand_total = int(grand_total_m.group(1).replace(',', '')) if grand_total_m else None
    pay_date = f'{pay_year}-{int(pay_month):02d}-{int(pay_day):02d}' if pay_year else None

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
    statements.append({
        'file': base, 'pay_date': pay_date, 'grand_total': grand_total,
        'parsed_sum': parsed_sum, 'match': parsed_sum == grand_total,
        'n_txns': len(txns), 'unmatched_lines': unmatched, 'txns': txns,
    })

rows = []
for s in statements:
    pay_month_label = f'{int(s["pay_date"].split("-")[1])}月' if s['pay_date'] else None
    for t in s['txns']:
        yy, mm, dd = t['date'].split('/')
        use_date = f'20{yy}-{mm}-{dd}'
        name = t['name']
        memo = t['memo']
        # PDF layout artifact: this row is really the cash-advance interest
        # line, not a second charge at the same merchant (see ※海外キャッシュ
        # サービスご返済合計金額※ = 10,615 + 146 in the July statement).
        if name.strip() == 'PZA DELLA VITTORIA 28 (ANACAPRI )' and t['amount'] == 146:
            name = '海外キャッシュサービス利息'
            memo = '(海外キャッシュサービス ご返済期間28日間)'
        rows.append({
            'use_date': use_date,
            'name': name,
            'amount': t['amount'],
            'memo': memo,
            'pay_date': s['pay_date'],
            'pay_month_label': pay_month_label,
            'category': categorize(name, memo),
        })

rows.sort(key=lambda r: (r['pay_date'], r['use_date']))

for s in statements:
    print(s['file'], s['pay_date'], 'grand_total=', s['grand_total'], 'parsed_sum=', s['parsed_sum'],
          'match=', s['match'], 'n=', s['n_txns'])
    if s['unmatched_lines']:
        print('  UNMATCHED:', s['unmatched_lines'])

from collections import Counter
cat_counts = Counter(r['category'] for r in rows)
print('\n=== category counts ===')
for c, n in cat_counts.most_common():
    print(c, n)
others = [r for r in rows if r['category'] == 'その他']
print('\n=== uncategorized (その他) sample, n=', len(others), '===')
for r in others:
    print(r['use_date'], r['name'], r['amount'], '|', r['memo'])

print('\nTOTAL rows:', len(rows), 'TOTAL amount:', sum(r['amount'] for r in rows))

with open(os.path.join(ROOT, 'data', 'sumitomo_transactions.json'), 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
