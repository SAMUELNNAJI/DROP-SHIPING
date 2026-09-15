# -*- coding: utf-8 -*-
"""P10b: dashboards.css — topbar v3 (glass rail)."""
from pathlib import Path

def load(p): return Path(p).read_text(encoding='utf-8')
def save(p, t): Path(p).write_text(t, encoding='utf-8'); print('  saved %s (%d bytes)' % (p, len(t)))

P = 'static/dashboards.css'
t = load(P)
if 'topbar v3' in t:
    print('  already patched')
else:
    t += (
        '\n/* ═══ topbar v3 — unified glass rail (all roles) ═══ */\n'
        '.dashboard-topbar{position:sticky;top:0;z-index:15;display:flex;align-items:center;gap:16px;min-height:80px;padding:0 30px;'
        'background:rgba(255,255,255,.74);backdrop-filter:blur(20px) saturate(160%);-webkit-backdrop-filter:blur(20px) saturate(160%);'
        'border-bottom:1px solid rgba(20,40,90,.08);box-shadow:0 10px 30px rgba(16,42,98,.06)}\n'
        '.dashboard-topbar-title{display:flex;align-items:center;gap:14px;min-width:0}\n'
        '.dashboard-topbar-title h1{margin:2px 0 0;font-size:21px;font-weight:800;letter-spacing:-.035em;line-height:1.2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}\n'
        '.dashboard-topbar-title p{margin:0;font-size:11.5px;font-weight:600;color:#5d6a85}\n'
        '.stop__crumbs{display:flex;align-items:center;gap:7px;margin:0;font-size:10.5px;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#93a0bd}\n'
        '.stop__crumbs .sic{width:13px;height:13px;color:#b6c1d8}\n'
        '.dashboard-topbar-actions{margin-left:auto;display:flex;align-items:center;gap:11px}\n'
        '.dashboard-topbar .seller-search,.dashboard-topbar .btop__search,.dashboard-topbar .atop__search{display:flex;align-items:center;gap:9px;width:250px;height:44px;padding:0 15px;border-radius:13px;background:rgba(240,244,253,.85);border:1px solid rgba(20,40,90,.10);color:#93a0bd;transition:border-color .18s,box-shadow .18s,background .18s}\n'
        '.dashboard-topbar .seller-search:focus-within,.dashboard-topbar .btop__search:focus-within,.dashboard-topbar .atop__search:focus-within{border-color:rgba(36,86,230,.45);box-shadow:0 0 0 3px rgba(36,86,230,.13);background:#fff;color:#2456e6}\n'
        '.dashboard-topbar .seller-search input,.dashboard-topbar .btop__search input,.dashboard-topbar .atop__search input{border:0;background:none;outline:0;font:inherit;font-size:13px;color:#16223c;width:100%}\n'
        '.dashboard-topbar .seller-search input::placeholder,.dashboard-topbar .btop__search input::placeholder,.dashboard-topbar .atop__search input::placeholder{color:#93a0bd}\n'
        '.dashboard-topbar .seller-icon-btn,.dashboard-topbar .btop__icon,.dashboard-topbar .atop__icon{position:relative;width:44px;height:44px;border-radius:13px;display:grid;place-items:center;background:rgba(240,244,253,.85);border:1px solid rgba(20,40,90,.10);color:#4c5a77;text-decoration:none;cursor:pointer;transition:background .18s,color .18s,border-color .18s}\n'
        '.dashboard-topbar .seller-icon-btn:hover,.dashboard-topbar .btop__icon:hover,.dashboard-topbar .atop__icon:hover{background:#fff;color:#2456e6;border-color:rgba(36,86,230,.35)}\n'
        '.dashboard-topbar .seller-icon-btn .sic,.dashboard-topbar .btop__icon .sic,.dashboard-topbar .atop__icon .sic{width:19px;height:19px}\n'
        '.dashboard-topbar .seller-icon-btn i,.dashboard-topbar .btop__icon i,.dashboard-topbar .atop__icon i{position:absolute;top:10px;right:11px;width:7px;height:7px;border-radius:50%;background:#e5484d;box-shadow:0 0 0 2px #fff}\n'
        '.dashboard-topbar .stop__logout,.dashboard-topbar .atop__logout{display:inline-flex;align-items:center;gap:8px;height:44px;padding:0 16px;border-radius:13px;border:1px solid rgba(229,72,77,.26);background:rgba(229,72,77,.07);color:#c23a3f;font:inherit;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;transition:background .18s,color .18s}\n'
        '.dashboard-topbar .stop__logout:hover,.dashboard-topbar .atop__logout:hover{background:rgba(229,72,77,.16)}\n'
        '.dashboard-topbar .stop__logout .sic,.dashboard-topbar .atop__logout .sic{width:16px;height:16px}\n'
        '.dashboard-topbar .seller-avatar,.dashboard-topbar .btop__avatar,.dashboard-topbar .atop__avatar{width:44px;height:44px;border-radius:13px;display:grid;place-items:center;background:linear-gradient(135deg,#2456e6,#4f8dff);color:#fff;font-weight:800;font-size:15px;text-decoration:none;box-shadow:0 10px 22px rgba(36,86,230,.30);flex-shrink:0}\n'
        '.dashboard-topbar .seller-top-btn{height:44px;border-radius:13px;background:linear-gradient(135deg,#2456e6,#1a41b4);color:#fff;font-weight:800;font-size:13px;box-shadow:0 12px 26px rgba(36,86,230,.32);border:0;cursor:pointer;display:inline-flex;align-items:center;gap:8px;padding:0 16px;transition:transform .16s,box-shadow .16s}\n'
        '.dashboard-topbar .seller-top-btn:hover{transform:translateY(-1px);box-shadow:0 16px 32px rgba(36,86,230,.40)}\n'
        '@media(max-width:800px){.dashboard-topbar{min-height:66px;padding:0 16px}.dashboard-topbar h1{font-size:17px}}\n')
    save(P, t)
print('p10b done')
