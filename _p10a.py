# -*- coding: utf-8 -*-
"""P10a: auth.css — desktop gap fix + login button redesign."""
from pathlib import Path

def load(p): return Path(p).read_text(encoding='utf-8')
def save(p, t): Path(p).write_text(t, encoding='utf-8'); print('  saved %s (%d bytes)' % (p, len(t)))

P = 'static/auth.css'
t = load(P)
t = t.replace(
    '.auth-shell{background:linear-gradient(135deg,#e8f0ff 0%,#d7e4fa 100%);padding-top:max(var(--header-h),env(safe-area-inset-top));min-height:100vh;}',
    '.auth-shell{background:linear-gradient(135deg,#e8f0ff 0%,#d7e4fa 100%);min-height:100vh;}', 1)
t = t.replace(
    '@media(max-width:760px){.auth-shell{display:block;min-height:0}',
    '@media(max-width:760px){.auth-shell{display:block;min-height:0;padding-top:max(var(--header-h),env(safe-area-inset-top))}', 1)
t += (
    '\n/* ── Sign-in / sign-up submit button v2 ── */\n'
    '.auth-submit{display:flex;align-items:center;justify-content:center;gap:10px;width:100%;min-height:53px;'
    'border:0;border-radius:15px;cursor:pointer;font:inherit;font-size:15px;font-weight:800;letter-spacing:-.01em;'
    'color:#fff;background:linear-gradient(135deg,#2f6bff 0%,#1a41b4 100%);'
    'box-shadow:0 14px 30px rgba(26,65,180,.34),inset 0 1px 0 rgba(255,255,255,.25);'
    'transition:transform .18s,box-shadow .18s,filter .18s}\n'
    '.auth-submit:hover{transform:translateY(-2px);box-shadow:0 20px 42px rgba(26,65,180,.42);filter:saturate(1.12)}\n'
    '.auth-submit:active{transform:translateY(0);box-shadow:0 8px 20px rgba(26,65,180,.34)}\n'
    '.auth-submit svg{width:18px;height:18px;transition:transform .18s}\n'
    '.auth-submit:hover svg{transform:translateX(4px)}\n'
    '.auth-submit:focus-visible{outline:3px solid rgba(47,107,255,.35);outline-offset:2px}\n')
save(P, t)
print('p10a done')
