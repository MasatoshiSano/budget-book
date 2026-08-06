# -*- coding: utf-8 -*-
# Parses PayPayカード statement CSVs (data/raw/paypay/*.csv) into
# data/paypay_transactions.json. To add a new month: save the new statement
# CSV into data/raw/paypay/ (any filename) and re-run this script — pay_month
# is read from each row's own "当月お支払日" column, not from the filename.
import csv, json, glob, os, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, 'data', 'raw', 'paypay')
FILES = sorted(glob.glob(os.path.join(DIR, '*.csv')))

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

RULES = [
    ('通信費・サブスク', ['ｐｏｖｏご利用料金', 'ＧＯＯＧＬＥ ＧＯＯＧＬＥ ＯＮＥ', 'ＧＯＯＧＬＥ ＰＬＡＹ ＪＡＰＡＮ',
                      'ＧＯＯＧＬＥ ＭＯＮＥＹＦＯＲＷＡＲＤＨＭ', 'ＡＮＴＨＲＯＰＩＣ', 'ＣＬＡＵＤＥ．ＡＩ ＳＵＢＳＣＲＩＰＴＩ',
                      'ＡＭＡＺＯＮ ＷＥＢ ＳＥＲＶＩＣＥＳ', 'AMAZON WEB SERVICES', 'ＬＩＮＥ ＥＣ']),
    ('交通費', ['モバイルＩＣＯＣＡ', 'タイムズパーキング', 'ＯｎｅＰａｒｋ', 'ＥＮＥＯＳ', 'ｱﾎﾟﾛｽﾃ-ｼﾖﾝ', 'ＪＲ', '駐車場']),
    ('美容・健康', ['ｃｈｏｃｏＺＡＰ', 'ＦＲＩＳＥＵＲ', 'ＤＥＬＩＧＨＴ ＨＡＩＲ', 'スパ＆ケア ヤスムラ', 'ホームドライ', 'アクセア']),
    ('旅行・宿泊', ['ホテル', 'ユーケーホテルマネジメント']),
    ('教育・資格', ['ＴＥＳＴＩＮＧ ＥＸＡＭ', 'ＶＵＥ']),
    ('コンビニ', ['セブンーイレブン', 'ローソン', 'ファミリーマート']),
    ('ドラッグストア', ['スギ薬局グループ']),
    ('スーパー・食料品', ['イズミヤ', 'ダイエー', 'コストコ ホールセール ジャパン', 'コストコホールセールジャパン']),
    ('外食・カフェ', [
        'コメダ珈琲店', 'サンマルクカフェ', 'ドトールコーヒーショップ', 'ケンタッキーフライドチキン', 'モスバーガー',
        'スターバックス コーヒー', 'インド料理 アカーシュ', '和食ダイニング 白鷺亭', 'コーヒーハウスフィールド',
        'サケトメシ', 'ＣＲＥＰＥ ＤＥ ＧＩＲＡ', 'フォンテカ゛ーラ', 'フォンテガーラ', 'アイスるんです',
        'ブランジェリー コム・シノ', '今八商店', 'ケーズ ケベック', 'Ｃｏｋｅ ＯＮ', 'ｼﾕﾊﾘ ﾄﾞｳｼﾞﾏﾃﾝ',
        'ﾜｼﾖｸｻﾄ', '関西キリンビバレッジサービ', 'ジハンピ', '道の駅',
    ]),
    ('日用品・インテリア', ['ダイソー', 'ニトリ', 'ロフト', 'ロイヤルホームセンター', 'ホームセンターコーナン', 'イケア']),
    ('ファッション・美容', ['ユニクロ', 'ユナイテッドアローズアウト']),
    ('ショッピングモール・百貨店', ['阪急阪神百貨店', 'ピオレ姫路', 'ミント神戸', '神戸三田プレミアムアウトレ',
                              '三井アウトレットパークジャ', 'ＫＩＴＴＥ大阪', 'ｅｋｉｍｏ梅田', '阪急西宮ガーデンズ',
                              '阪急阪神エキナカ店舗']),
]

def categorize(name):
    hay = norm(name)
    for cat, kws in RULES:
        for kw in kws:
            if norm(kw) in hay:
                return cat
    return 'その他'

def pay_month_label_of(pay_date):
    # pay_date is 'YYYY/M/D' (not zero-padded)
    return f'{int(pay_date.split("/")[1])}月'

rows = []
for path in FILES:
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            if not r.get('利用日/キャンセル日'):
                continue
            amt_s = r['利用金額'].strip()
            if amt_s == '':
                continue
            amount = int(amt_s.replace(',', ''))
            name = r['利用店名・商品名'].strip()
            pay_date = r['当月お支払日'].strip()
            rows.append({
                'use_date': r['利用日/キャンセル日'].strip(),
                'name': name,
                'payment_method': r['決済方法'].strip(),
                'amount': amount,
                'pay_date': pay_date,
                'pay_month_label': pay_month_label_of(pay_date),
                'category': categorize(name),
            })

# sort chronologically by pay_date (not the "N月" label, which doesn't sort right).
# pay_date isn't zero-padded ("2026/7/27"), so compare the y/m/d parts as ints.
def date_sort_key(s):
    return tuple(int(p) for p in s.replace('/', '-').split('-'))
rows.sort(key=lambda r: (date_sort_key(r['pay_date']), date_sort_key(r['use_date'])))

from collections import Counter
cat_counts = Counter(r['category'] for r in rows)
print('=== category counts ===')
for c, n in cat_counts.most_common():
    print(c, n)

others = [r for r in rows if r['category'] == 'その他']
print('\n=== uncategorized (その他), n=', len(others), '===')
for r in others:
    print(r['use_date'], r['name'], r['amount'])

# cross check totals per statement file against sum of 当月支払金額 column (support separately)
totals_by_file = {}
for path in FILES:
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        tot = 0
        for r in reader:
            if not r.get('利用日/キャンセル日'):
                continue
            v = r['当月支払金額'].strip()
            if v == '':
                continue
            tot += int(v.replace(',', ''))
        totals_by_file[os.path.basename(path)] = tot

print('\n=== monthly 当月支払金額 totals (from CSV column) ===')
for fname, tot in totals_by_file.items():
    print(fname, tot)

parsed_sum_by_month = Counter()
for r in rows:
    parsed_sum_by_month[r['pay_month_label']] += r['amount']
print('\n=== monthly parsed 利用金額 sums (cancellations netted) ===')
for label, tot in sorted(parsed_sum_by_month.items(), key=lambda kv: int(kv[0].rstrip('月'))):
    print(label, tot)

print('\nTOTAL rows:', len(rows), 'TOTAL amount (利用金額 net):', sum(r['amount'] for r in rows))

with open(os.path.join(ROOT, 'data', 'paypay_transactions.json'), 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
