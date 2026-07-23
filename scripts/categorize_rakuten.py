# -*- coding: utf-8 -*-
import json, unicodedata
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/rakuten_parsed.json', encoding='utf-8') as f:
    statements = json.load(f)

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

rows = []
for s in statements:
    for t in s['txns']:
        rows.append({
            'use_date': t['date'],
            'name': t['name'],
            'user': t['user'],
            'method': t['method'],
            'amount': t['amount'],
            'pay_month_label': s['label'],
            'category': categorize(t['name']),
        })

rows.sort(key=lambda r: (r['pay_month_label'], r['use_date']))

from collections import Counter
cat_counts = Counter(r['category'] for r in rows)
print('=== category counts ===')
for c, n in cat_counts.most_common():
    print(c, n)
others = [r for r in rows if r['category'] == 'その他']
print('その他 rows:', others)
print('TOTAL:', len(rows), sum(r['amount'] for r in rows))

with open('/tmp/claude-0/-home-user-budget-book/02b55f01-b334-5b26-9fc8-6e95ce3af906/scratchpad/rakuten_rows.json', 'w', encoding='utf-8') as f:
    json.dump(rows, f, ensure_ascii=False, indent=2)

# ---------------- build xlsx ----------------
FONT_NAME = 'Arial'
BASE_FONT = Font(name=FONT_NAME, size=10)
HEADER_FONT = Font(name=FONT_NAME, size=10, bold=True, color='FFFFFF')
HEADER_FILL = PatternFill('solid', fgColor='BF0000')  # Rakuten red
BOLD = Font(name=FONT_NAME, size=10, bold=True)
TITLE_FONT = Font(name=FONT_NAME, size=14, bold=True)
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
MONEY_FMT_PLAIN = '#,##0'

PAY_MONTHS = ['1月', '2月', '3月', '4月', '5月', '6月', '7月']
PAY_MONTH_TO_DATE = {s['label']: None for s in statements}
for s in statements:
    # derive pay date from filename month + fixed day pattern seen in text (27th, except Jan/Jun 29th... use per-file known dates)
    pass
PAY_DATES = {
    '1月': '2026/01/27', '2月': '2026/02/27', '3月': '2026/03/27', '4月': '2026/04/27',
    '5月': '2026/05/27', '6月': '2026/06/29', '7月': '2026/07/27',
}

CATEGORY_ORDER = ['投資', '電子マネー・チャージ', '通信費・サブスク', '交通費', 'ネットショッピング', 'スーパー・食料品', 'その他']

wb = Workbook()
ws = wb.active
ws.title = '明細'
headers = ['利用日', '利用店名', 'カテゴリ', '利用者', '支払方法', '金額', 'お支払月']
widths = [12, 34, 20, 10, 12, 12, 10]
for i, (h, w) in enumerate(zip(headers, widths), start=1):
    c = ws.cell(row=1, column=i, value=h)
    c.font = HEADER_FONT
    c.fill = HEADER_FILL
    c.alignment = Alignment(horizontal='center')
    ws.column_dimensions[get_column_letter(i)].width = w
ws.freeze_panes = 'A2'

for r, row in enumerate(rows, start=2):
    ws.cell(row=r, column=1, value=row['use_date']).font = BASE_FONT
    ws.cell(row=r, column=2, value=row['name']).font = BASE_FONT
    ws.cell(row=r, column=3, value=row['category']).font = BASE_FONT
    ws.cell(row=r, column=4, value=row['user']).font = BASE_FONT
    ws.cell(row=r, column=5, value=row['method']).font = BASE_FONT
    amt_cell = ws.cell(row=r, column=6, value=row['amount'])
    amt_cell.font = BASE_FONT
    amt_cell.number_format = MONEY_FMT_PLAIN
    ws.cell(row=r, column=7, value=row['pay_month_label']).font = BASE_FONT
    for col in range(1, 8):
        ws.cell(row=r, column=col).border = BORDER

last_row = len(rows) + 1
total_row = last_row + 1
ws.cell(row=total_row, column=3, value='合計').font = BOLD
tc = ws.cell(row=total_row, column=6, value=f'=SUM(F2:F{last_row})')
tc.font = BOLD
tc.number_format = MONEY_FMT_PLAIN

# ---------------- Sheet 2: 月別サマリー ----------------
ws2 = wb.create_sheet('月別サマリー')
ws2['A1'] = '楽天カード ご利用明細 月別×カテゴリ集計（お支払月ベース）'
ws2['A1'].font = TITLE_FONT
ws2.merge_cells('A1:I1')

header_row = 3
ws2.cell(row=header_row, column=1, value='カテゴリ').font = HEADER_FONT
ws2.cell(row=header_row, column=1).fill = HEADER_FILL
ws2.column_dimensions['A'].width = 24
for i, m in enumerate(PAY_MONTHS, start=2):
    c = ws2.cell(row=header_row, column=i, value=f'{m}(支払)')
    c.font = HEADER_FONT
    c.fill = HEADER_FILL
    c.alignment = Alignment(horizontal='center')
    ws2.column_dimensions[get_column_letter(i)].width = 13
total_col = 2 + len(PAY_MONTHS)
c = ws2.cell(row=header_row, column=total_col, value='合計')
c.font = HEADER_FONT
c.fill = HEADER_FILL
ws2.column_dimensions[get_column_letter(total_col)].width = 14

detail_last_row = last_row
for ri, cat in enumerate(CATEGORY_ORDER, start=header_row + 1):
    ws2.cell(row=ri, column=1, value=cat).font = BASE_FONT
    for ci, m in enumerate(PAY_MONTHS, start=2):
        col_letter = get_column_letter(ci)
        formula = (f'=SUMIFS(明細!$F$2:$F${detail_last_row},'
                   f'明細!$C$2:$C${detail_last_row},$A{ri},'
                   f'明細!$G$2:$G${detail_last_row},{col_letter}${header_row})')
        cell = ws2.cell(row=ri, column=ci, value=formula)
        cell.number_format = MONEY_FMT_PLAIN
        cell.font = BASE_FONT
    tcell = ws2.cell(row=ri, column=total_col,
                      value=f'=SUM(B{ri}:{get_column_letter(total_col - 1)}{ri})')
    tcell.font = BOLD
    tcell.number_format = MONEY_FMT_PLAIN
    for col in range(1, total_col + 1):
        ws2.cell(row=ri, column=col).border = BORDER

grand_row = header_row + len(CATEGORY_ORDER) + 1
ws2.cell(row=grand_row, column=1, value='合計').font = BOLD
for ci in range(2, total_col + 1):
    col_letter = get_column_letter(ci)
    top = header_row + 1
    bottom = grand_row - 1
    cell = ws2.cell(row=grand_row, column=ci,
                     value=f'=SUM({col_letter}{top}:{col_letter}{bottom})')
    cell.font = BOLD
    cell.number_format = MONEY_FMT_PLAIN
    cell.border = BORDER
ws2.cell(row=grand_row, column=1).border = BORDER
ws2.freeze_panes = ws2.cell(row=header_row + 1, column=2).coordinate

ref_row = grand_row + 2
ws2.cell(row=ref_row, column=1,
         value='参考：各月の「ご請求金額」（明細書記載）。2月は調整額-23,044円・返金26,950円が発生したため、明細合計23,044円に対し請求額は0円。').font = BOLD
ws2.merge_cells(start_row=ref_row, start_column=1, end_row=ref_row, end_column=total_col)
ws2.cell(row=ref_row, column=1).alignment = Alignment(wrap_text=True)
ws2.cell(row=ref_row + 1, column=1, value='お支払月').font = HEADER_FONT
ws2.cell(row=ref_row + 1, column=1).fill = HEADER_FILL
ws2.cell(row=ref_row + 1, column=2, value='お支払日').font = HEADER_FONT
ws2.cell(row=ref_row + 1, column=2).fill = HEADER_FILL
ws2.cell(row=ref_row + 1, column=3, value='ご請求金額(明細書記載)').font = HEADER_FONT
ws2.cell(row=ref_row + 1, column=3).fill = HEADER_FILL
for i, m in enumerate(PAY_MONTHS):
    r = ref_row + 2 + i
    s = statements[i]
    ws2.cell(row=r, column=1, value=f'{m}(支払)').font = BASE_FONT
    ws2.cell(row=r, column=2, value=PAY_DATES[m]).font = BASE_FONT
    cell = ws2.cell(row=r, column=3, value=s['header_total'])
    cell.font = BASE_FONT
    cell.number_format = MONEY_FMT_PLAIN
    for col in range(1, 4):
        ws2.cell(row=r, column=col).border = BORDER

# ---------------- Sheet 3: カテゴリ別集計 ----------------
ws3 = wb.create_sheet('カテゴリ別集計')
ws3['A1'] = 'カテゴリ別集計（2026年1月〜7月支払 全体）'
ws3['A1'].font = TITLE_FONT
ws3.merge_cells('A1:D1')
h3 = 3
for i, h in enumerate(['カテゴリ', '金額', '構成比', ''], start=1):
    c = ws3.cell(row=h3, column=i, value=h)
    c.font = HEADER_FONT
    c.fill = HEADER_FILL
ws3.column_dimensions['A'].width = 24
ws3.column_dimensions['B'].width = 14
ws3.column_dimensions['C'].width = 10
ws3.column_dimensions['D'].width = 30

for ri, cat in enumerate(CATEGORY_ORDER, start=h3 + 1):
    ws3.cell(row=ri, column=1, value=cat).font = BASE_FONT
    amt_formula = f'=SUMIF(明細!$C$2:$C${detail_last_row},$A{ri},明細!$F$2:$F${detail_last_row})'
    acell = ws3.cell(row=ri, column=2, value=amt_formula)
    acell.font = BASE_FONT
    acell.number_format = MONEY_FMT_PLAIN
    pcell = ws3.cell(row=ri, column=3, value=f'=B{ri}/$B${h3 + len(CATEGORY_ORDER) + 1}')
    pcell.font = BASE_FONT
    pcell.number_format = '0.0%'
    for col in range(1, 4):
        ws3.cell(row=ri, column=col).border = BORDER

g3 = h3 + len(CATEGORY_ORDER) + 1
ws3.cell(row=g3, column=1, value='合計').font = BOLD
gcell = ws3.cell(row=g3, column=2, value=f'=SUM(B{h3+1}:B{g3-1})')
gcell.font = BOLD
gcell.number_format = MONEY_FMT_PLAIN
ws3.cell(row=g3, column=3, value=f'=B{g3}/B{g3}').number_format = '0.0%'
ws3.cell(row=g3, column=3).font = BOLD
for col in range(1, 4):
    ws3.cell(row=g3, column=col).border = BORDER

wb.save('/home/user/budget-book/rakuten_card_2026_01-07.xlsx')
print('saved')
