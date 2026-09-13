# -*- coding: utf-8 -*-
"""Sanity-check the checkout/auth pages + CSS after the chrome transplant."""
import io, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

for f in ['checkout.html', 'checkout-payment.html', 'checkout-success.html', 'signin.html']:
    t = io.open(f, encoding='utf-8', newline='').read()
    print('%-24s navbar:%d sitefooter:%d drawer:%d cartDD:%d oldauthfooter:%d aboutActive:%d chromeJS:%s'
          % (f,
             t.count('<header class="navbar">'),
             t.count('<footer class="footer">'),
             t.count('id="mobileMenu"'),
             t.count('id="cartDropdown"'),
             t.count('class="auth-footer"'),
             t.count('aria-current="page">About'),
             'yes' if 'Mobile drawer menu listener' in t else 'NO'))

for c in ['auth.css', 'checkout.css', 'style.css']:
    s = io.open(c, encoding='utf-8', newline='').read()
    print('%-12s braces balanced: %s (%d open / %d close)' % (c, s.count('{') == s.count('}'), s.count('{'), s.count('}')))

print('done')