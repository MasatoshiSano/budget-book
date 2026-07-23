# -*- coding: utf-8 -*-
import json, re, unicodedata

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/parsed.json', encoding='utf-8') as f:
    statements = json.load(f)

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

def categorize(name, memo):
    hay = norm(name) + ' ' + norm(memo)
    for cat, kws in RULES:
        for kw in kws:
            if kw and norm(kw) in hay:
                return cat
    return 'その他'

FILE_LABEL = {
    '8ba385a4-_______2026_1_.pdf': '1月',
    '5ffb4644-_______2026_2_.pdf': '2月',
    '890929e2-_______2026_3_.pdf': '3月',
    'b47794e5-_______2026_4_.pdf': '4月',
    '19221789-_______2026_5_.pdf': '5月',
    '4fb6534b-_______2026_6_.pdf': '6月',
    '10fadd8a-_______2026_7_.pdf': '7月',
}

rows = []
for s in statements:
    pay_month_label = FILE_LABEL[s['file']]
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
        cat = categorize(name, memo)
        rows.append({
            'use_date': use_date,
            'name': name,
            'amount': t['amount'],
            'memo': memo,
            'pay_date': s['pay_date'],
            'pay_month_label': pay_month_label,
            'category': cat,
        })

rows.sort(key=lambda r: (r['pay_date'], r['use_date']))

# stats
from collections import Counter, defaultdict
cat_counts = Counter(r['category'] for r in rows)
print('=== category counts ===')
for c, n in cat_counts.most_common():
    print(c, n)

others = [r for r in rows if r['category'] == 'その他']
print('\n=== uncategorized (その他) sample, n=', len(others), '===')
for r in others:
    print(r['use_date'], r['name'], r['amount'], '|', r['memo'])

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/rows.json', 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

print('\nTOTAL rows:', len(rows), 'TOTAL amount:', sum(r['amount'] for r in rows))
