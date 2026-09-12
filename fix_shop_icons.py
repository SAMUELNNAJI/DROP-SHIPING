#!/usr/bin/env python3
"""Replace the search emoji in shop.html empty state with a proper SVG, then clean temp files."""
import os

BASE = r'c:\Users\ADMIN\Desktop\DROP SHIPING'
os.chdir(BASE)

# 1) Replace the search emoji
p = os.path.join(BASE, 'shop.html')
txt = open(p, encoding='utf-8').read()

BAD = '<span class="shop-empty-ico">🔍</span>'
GOOD = ('<svg class="shop-empty-ico" width="48" height="48" viewBox="0 0 24 24" '
        'fill="none" stroke="#C8D4E6" stroke-width="1.6" stroke-linecap="round">'
        '<circle cx="11" cy="11" r="7"/>'
        '<line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>')

if BAD in txt:
    txt = txt.replace(BAD, GOOD)
    open(p, 'w', encoding='utf-8').write(txt)
    print('shop.html: replaced search emoji → SVG')
else:
    print('shop.html: no search emoji found (already fixed?)')

# 2) Clean temp files
removed = []
for f in os.listdir(BASE):
    if f.startswith('_') and os.path.isfile(os.path.join(BASE, f)):
        try:
            os.remove(os.path.join(BASE, f))
            removed.append(f)
        except Exception as e:
            removed.append(f'{f} → ERROR {e}')
for r in removed:
    print(f'cleaned: {r}')
print(f'\nTotal cleaned: {len(removed)}')
