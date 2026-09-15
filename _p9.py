# -*- coding: utf-8 -*-
"""P9: auth-aware header across all site templates.
When signed in: Sign In / Start Selling (desktop + mobile menu) -> Dashboard button."""
from pathlib import Path
import re

DASH_HREF = ("{% if user.is_superuser %}/dashboards/admin/{% elif user.role == 'seller' %}"
             "/dashboards/seller/{% else %}/dashboards/buyer/{% endif %}")

DASH_DESKTOP = (
    '<a href="' + DASH_HREF + '" class="btn-sell"><span>Dashboard</span>'
    '<svg class="btn-sell-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
    '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></a>'
)
DASH_MOBILE = (
    '<a href="' + DASH_HREF + '" class="mmenu-cta"><span>Dashboard</span>'
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/>'
    '<rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg></a>'
)

RX_NAV_SIGNIN = re.compile(r'<a href="[^"]*" class="nav-signin[^"]*"[^>]*>[\s\S]*?</a>')
RX_BTN_SELL = re.compile(r'<a href="[^"]*" class="btn-sell"[^>]*>[\s\S]*?</a>')
RX_MMENU_CTA = re.compile(r'<a href="[^"]*" class="mmenu-cta"[^>]*>[\s\S]*?</a>')
RX_MMENU_SIGNIN = re.compile(r'<a href="[^"]*" class="mmenu-signin"[^>]*>[\s\S]*?</a>')

files = sorted(Path('templates').glob('*.html')) + [Path('templates/auth/header.html')]
total = 0
for p in files:
    if not p.exists():
        continue
    t = p.read_text(encoding='utf-8')
    orig = t
    if 'nav-signin' in t:
        t = RX_NAV_SIGNIN.sub(lambda m: '{% if not user.is_authenticated %}' + m.group(0) + '{% endif %}', t)
    if 'btn-sell' in t:
        t = RX_BTN_SELL.sub(lambda m: '{% if user.is_authenticated %}' + DASH_DESKTOP + '{% else %}' + m.group(0) + '{% endif %}', t)
    if 'mmenu-cta' in t:
        t = RX_MMENU_CTA.sub(lambda m: '{% if user.is_authenticated %}' + DASH_MOBILE + '{% else %}' + m.group(0) + '{% endif %}', t)
    if 'mmenu-signin' in t:
        t = RX_MMENU_SIGNIN.sub(lambda m: '{% if not user.is_authenticated %}' + m.group(0) + '{% endif %}', t)
    if t != orig:
        p.write_text(t, encoding='utf-8')
        total += 1
        print('  patched', p.name)
print('files patched:', total)
