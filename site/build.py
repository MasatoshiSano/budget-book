# -*- coding: utf-8 -*-
# Rebuilds site/index.html from site/template.html + data/unified_transactions.json.
# Run this after scripts/consolidate.py whenever new statements are added.
import json
import os
import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'site')
DATA = os.path.join(ROOT, 'data')

with open(os.path.join(SITE, 'fonts', 'manrope-var.b64')) as f:
    manrope_b64 = f.read().strip()
with open(os.path.join(SITE, 'fonts', 'plexmono-500.b64')) as f:
    plex500_b64 = f.read().strip()
with open(os.path.join(SITE, 'fonts', 'plexmono-600.b64')) as f:
    plex600_b64 = f.read().strip()

with open(os.path.join(DATA, 'unified_transactions.json'), encoding='utf-8') as f:
    data = json.load(f)
data_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))

with open(os.path.join(SITE, 'template.html'), encoding='utf-8') as f:
    tpl = f.read()

now = datetime.date.today().strftime('%Y年%m月%d日')

out = tpl.replace('__MANROPE_B64__', manrope_b64)
out = out.replace('__PLEX500_B64__', plex500_b64)
out = out.replace('__PLEX600_B64__', plex600_b64)
out = out.replace('__DATA_JSON__', data_json)
out = out.replace('__GENERATED_AT__', now)

with open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(out)

print('built, size =', len(out), 'bytes,', len(data), 'transactions')
