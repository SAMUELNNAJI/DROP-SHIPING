# -*- coding: utf-8 -*-
"""P11a: sidebar height auto — in-flow column (desktop), drawer (mobile)."""
from pathlib import Path

def load(p): return Path(p).read_text(encoding='utf-8')
def save(p, t): Path(p).write_text(t, encoding='utf-8'); print('  saved %s (%d bytes)' % (p, len(t)))

# ── admin.css: base rule → in-flow; workspace → flex ──
P = 'static/admin.css'
t = load(P)
t = t.replace(
    '  position:fixed;top:0;left:0;bottom:auto;min-height:100vh;height:auto;max-height:100dvh;overflow-y:auto;overscroll-behavior:contain;',
    '  position:relative;top:auto;left:auto;bottom:auto;right:auto;min-height:0;height:auto;overflow:visible;flex-shrink:0;', 1)
t = t.replace(
    'body.dashboard-body--admin .dashboard-workspace{width:calc(100% - 284px);margin-left:284px;background:transparent;min-height:100vh;display:flex;flex-direction:column}',
    'body.dashboard-body--admin .dashboard-workspace{width:auto;flex:1;min-width:0;margin-left:0;background:transparent;min-height:100vh;display:flex;flex-direction:column}', 1)
t += (
    '\n/* drawer on mobile: fixed, full-height, internally scrollable */\n'
    '@media(max-width:800px){'
    'body.dashboard-body--admin .dashboard-sidebar{position:fixed;top:0;left:0;bottom:0;width:290px;height:100vh;max-height:100dvh;overflow-y:auto;transform:translateX(-100%);transition:transform .26s ease}'
    'body.dashboard-body--admin .dashboard-sidebar.is-open{transform:translateX(0)}'
    '}\n')
save(P, t)

# ── seller.css ──
P = 'static/seller.css'
t = load(P)
t = t.replace(
    'body.dashboard-body--seller .sside{top:0;left:0;bottom:auto;height:auto;min-height:100vh;max-height:100dvh;overflow-y:auto;overscroll-behavior:contain}',
    'body.dashboard-body--seller .sside{position:relative;top:auto;left:auto;bottom:auto;right:auto;width:276px;flex-shrink:0;height:auto;min-height:0;overflow:visible}\n'
    'body.dashboard-body--seller .dashboard-workspace{width:auto;flex:1;min-width:0;margin-left:0;min-height:100vh}', 1)
t += (
    '\n@media(max-width:800px){'
    'body.dashboard-body--seller .sside{position:fixed;top:0;left:0;bottom:0;width:284px;height:100vh;max-height:100dvh;overflow-y:auto}'
    '}\n')
save(P, t)

# ── buyer.css ──
P = 'static/buyer.css'
t = load(P)
t = t.replace(
    'body.dashboard-body--buyer .bside{top:0;left:0;bottom:auto;height:auto;min-height:100vh;max-height:100dvh;overflow-y:auto;overscroll-behavior:contain}',
    'body.dashboard-body--buyer .bside{position:relative;top:auto;left:auto;bottom:auto;right:auto;width:288px;flex-shrink:0;height:auto;min-height:0;overflow:visible}\n'
    'body.dashboard-body--buyer .dashboard-workspace{width:auto;flex:1;min-width:0;margin-left:0;min-height:100vh}', 1)
t += (
    '\n@media(max-width:800px){'
    'body.dashboard-body--buyer .bside{position:fixed;top:0;left:0;bottom:0;width:284px;height:100vh;max-height:100dvh;overflow-y:auto}'
    '}\n')
save(P, t)
print('p11a done')
