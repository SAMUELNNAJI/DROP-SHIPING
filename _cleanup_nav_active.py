# -*- coding: utf-8 -*-
"""Strip the 'About is current page' active state that was inherited from
about.html when the exact navbar/drawer were transplanted into the checkout
and auth pages (none of those pages is About)."""
import io, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

TARGETS = ['checkout.html', 'checkout-payment.html', 'checkout-success.html']

OLD_LINK = '<a href="about.html" class="active" aria-current="page">About</a>'
NEW_LINK = '<a href="about.html">About</a>'
OLD_DRAW = 'class="mmenu-link mmenu-link--active"'
NEW_DRAW = 'class="mmenu-link"'

for name in TARGETS:
    with io.open(name, 'r', encoding='utf-8', newline='') as fh:
        txt = fh.read()
    n1 = txt.count(OLD_LINK)
    n2 = txt.count(OLD_DRAW)
    txt = txt.replace(OLD_LINK, NEW_LINK).replace(OLD_DRAW, NEW_DRAW)
    with io.open(name, 'w', encoding='utf-8', newline='') as fh:
        fh.write(txt)
    print('%-24s nav-active removed:%d drawer-active removed:%d' % (name, n1, n2))

print('done')