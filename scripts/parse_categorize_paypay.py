# -*- coding: utf-8 -*-
import csv, json, glob, os, unicodedata

FILES = {
    '4c3357d0-detail2026013979.csv': '1月',
    'da5973f3-detail2026023979.csv': '2月',
    '97652b33-detail2026033979.csv': '3月',
    '7f76e1dd-detail2026043979.csv': '4月',
    '6595d659-detail2026053979.csv': '5月',
    '3cfde5dd-detail2026063979.csv': '6月',
    '4c6a7192-detail2026073979.csv': '7月',
}
DIR = '/root/.claude/uploads/02b55f01-b334-5b26-9fc8-6e95ce3af906'

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

rows = []
for fname, label in FILES.items():
    path = os.path.join(DIR, fname)
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
                'pay_month_label': label,
                'category': categorize(name),
            })

# sort
rows.sort(key=lambda r: (r['pay_month_label'], r['use_date']))

from collections import Counter
cat_counts = Counter(r['category'] for r in rows)
print('=== category counts ===')
for c, n in cat_counts.most_common():
    print(c, n)

others = [r for r in rows if r['category'] == 'その他']
print('\n=== uncategorized (その他), n=', len(others), '===')
for r in others:
    print(r['use_date'], r['name'], r['amount'])

# cross check totals per statement month against sum of 当月支払金額 column (support separately)
totals_by_month = {}
for fname, label in FILES.items():
    path = os.path.join(DIR, fname)
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
        totals_by_month[label] = tot

print('\n=== monthly 当月支払金額 totals (from CSV column) ===')
for label, tot in totals_by_month.items():
    print(label, tot)

parsed_sum_by_month = Counter()
for r in rows:
    parsed_sum_by_month[r['pay_month_label']] += r['amount']
print('\n=== monthly parsed 利用金額 sums (cancellations netted) ===')
for label in FILES.values():
    print(label, parsed_sum_by_month[label])

print('\nTOTAL rows:', len(rows), 'TOTAL amount (利用金額 net):', sum(r['amount'] for r in rows))

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/paypay_rows.json', 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)
