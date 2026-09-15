# -*- coding: utf-8 -*-
"""P10c: dashboards.css — pagination styles."""
from pathlib import Path

def load(p): return Path(p).read_text(encoding='utf-8')
def save(p, t): Path(p).write_text(t, encoding='utf-8'); print('  saved %s (%d bytes)' % (p, len(t)))

P = 'static/dashboards.css'
t = load(P)
if 'pgbar' in t:
    print('  already patched')
else:
    t += (
        '\n/* ═══ table pagination ═══ */\n'
        '.pgbar{display:flex;align-items:center;gap:7px;flex-wrap:wrap;padding:14px 22px;border-top:1px solid rgba(20,40,90,.08);background:rgba(240,244,253,.5)}\n'
        '.pginfo{font-size:12px;font-weight:700;color:#5d6a85;margin-right:auto}\n'
        '.pgbtn{min-width:36px;height:36px;padding:0 10px;border-radius:10px;border:1px solid rgba(20,40,90,.12);background:#fff;color:#43507a;font:inherit;font-size:12.5px;font-weight:800;cursor:pointer;display:inline-flex;align-items:center;justify-content:center;gap:6px;transition:border-color .16s,color .16s,background .16s,transform .16s}\n'
        '.pgbtn:hover:not(:disabled):not(.is-cur){border-color:rgba(36,86,230,.5);color:#2456e6;transform:translateY(-1px)}\n'
        '.pgbtn.is-cur{background:linear-gradient(135deg,#2456e6,#1a41b4);border-color:transparent;color:#fff;box-shadow:0 8px 18px rgba(36,86,230,.28)}\n'
        '.pgbtn:disabled{opacity:.4;cursor:default}\n'
        '.pgbtn .sic{width:14px;height:14px}\n')
    save(P, t)
print('p10c done')
