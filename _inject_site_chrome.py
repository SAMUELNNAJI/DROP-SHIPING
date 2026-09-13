# -*- coding: utf-8 -*-
"""
_inject_site_chrome.py
Transplants DropHub's EXACT site header (navbar + mobile drawer) and the
EXACT site footer (copied live from about.html) into the checkout + auth
pages, removing their old simplified navbar / minimal auth-footer, and
wires up the site header scripts (drawer + scroll state).
"""
import io, re, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

SRC = 'about.html'
TARGETS = ['checkout.html', 'checkout-payment.html', 'checkout-success.html', 'signin.html']

with io.open(SRC, 'r', encoding='utf-8', newline='') as fh:
    src = fh.read()

# ── 1. Extract the exact navbar + mobile drawer from about.html ──
m_head = re.search(
    r'<header class="navbar">.*?</header>\s*'
    r'(?:<!-- MOBILE / TABLET DRAWER MENU[^>]*-->\s*)?'
    r'(<div class="mmenu" id="mobileMenu".*?</aside>\s*</div>)',
    src, re.S)
assert m_head, 'navbar/drawer not found in ' + SRC
navbar = m_head.group(0)

# ── 2. Extract the exact site footer ──
m_foot = re.search(r'<footer class="footer">.*?</footer>', src, re.S)
assert m_foot, 'site footer not found in ' + SRC
footer = m_foot.group(0)

# ── 3. Extract the site header scripts (drawer + scroll + active links) ──
m_scr = re.search(
    r'<script>\s*document\.addEventListener\(\s*[\'"]DOMContentLoaded[\'"][\s\S]*?</script>',
    src)
assert m_scr, 'chrome script not found in ' + SRC
chrome = m_scr.group(0)
assert 'Mobile drawer menu listener' in chrome, 'unexpected script block'

for name in TARGETS:
    with io.open(name, 'r', encoding='utf-8', newline='') as fh:
        txt = fh.read()
    orig = txt

    nav = navbar
    if name == 'signin.html':
        # keep the page's own "Sign In is current" state in the exact header
        nav = nav.replace('class="nav-signin"', 'class="nav-signin active" aria-current="page"', 1)
        nav = nav.replace('stroke="#7B8798"', 'stroke="#1F64FF"', 1)
    # drawer sign-in shortcut should hit the real page (about.html used "#")
    nav = nav.replace('<a href="#" class="mmenu-signin">',
                      '<a href="signin.html" class="mmenu-signin">', 1)

    # A) swap the simplified navbar for the exact one (+ attach drawer)
    txt, n_nav = re.subn(r'<header class="navbar">.*?</header>',
                         lambda _m: nav, txt, count=1, flags=re.S)

    # B) swap the minimal auth-footer for the exact site footer
    txt, n_foot = re.subn(r'<footer class="auth-footer">.*?</footer>',
                          lambda _m: footer, txt, count=1, flags=re.S)

    # C) tidy the leftover "MINIMAL FOOTER" banner comment
    txt = re.sub(r'<!--\s*═+\s*MINIMAL FOOTER[\s\S]*?-->',
                 '<!-- Footer (Identical to Homepage) -->', txt)

    # D) add the header scripts before cart.js (once)
    scripts_added = 0
    if chrome not in txt:
        anchor = '<script src="cart.js"></script>'
        assert anchor in txt, 'cart.js anchor missing in ' + name
        txt = txt.replace(anchor, chrome + '\n\n' + anchor, 1)
        scripts_added = 1

    assert n_nav == 1, (name, 'navbar replacements', n_nav)
    assert n_foot == 1, (name, 'footer replacements', n_foot)

    if txt != orig:
        with io.open(name, 'w', encoding='utf-8', newline='') as fh:
            fh.write(txt)

    print('%-24s navbar:%d footer:%d scripts:%d' % (name, n_nav, n_foot, scripts_added))

print('done')