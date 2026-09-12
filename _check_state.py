#!/usr/bin/env python3
"""Check state of all pages for the DropHub nav/header fixes."""
import os, re

BASE = r'c:\Users\ADMIN\Desktop\DROP SHIPING'
os.chdir(BASE)

PAGES = ['index.html', 'shop.html', 'blog.html', 'about.html',
          'contact.html', 'help.html', 'refund-policy.html']

for fname in PAGES:
    with open(fname, 'rb') as f:
        txt = f.read().decode('utf-8', errors='replace')

    print(f'\n=== {fname} ===')

    # Desktop nav links
    nav_m = re.search(r'<nav class="nav-links">(.*?)</nav>', txt, re.DOTALL)
    if nav_m:
        links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', nav_m.group(1))
        print('  Desktop nav:')
        for href, label in links:
            print(f'    - {label} -> {href}')
    else:
        print('  NO nav-links found!')

    # Mobile menu nav links
    mmenu_m = re.search(r'<nav class="mmenu-nav">(.*?)</nav>', txt, re.DOTALL)
    if mmenu_m:
        mlinks = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', mmenu_m.group(1))
        print('  Mobile menu nav:')
        for href, label in mlinks:
            print(f'    - {label} -> {href}')
    else:
        print('  NO mmenu-nav found!')

    # Cart in mobile menu
    has_cart_menu = 'mmenu-link--cart' in txt
    print(f'  Cart in mobile menu: {has_cart_menu}')

    # cart.js included
    has_cart_js = '<script src="cart.js"' in txt or "<script src='cart.js'" in txt
    print(f'  cart.js referenced: {has_cart_js}')

    # Emoji icons in shop drawer (shop.html only)
    if fname == 'shop.html':
        emojis = [e for e in ['🔍','📦','💻','📱','👕','🏠','💄','🎒','📚','🛋️'] if e in txt]
        print(f'  Emoji icons in drawer: {emojis if emojis else "NONE"}')

    # rp-hero on refund page
    if fname == 'refund-policy.html':
        print(f'  Has rp-hero class: {"rp-hero" in txt}')

    # Contact page mobile full-width
    if fname == 'contact.html':
        print(f'  Has contact-section-mobile-full: {"contact-section-mobile-full" in txt}')

print('\n=== CSS checks ===')
for css_file in ['style.css', 'pages.css']:
    with open(css_file, 'rb') as f:
        css = f.read().decode('utf-8', errors='replace')
    print(f'\n{css_file}:')
    print(f'  cursor:pointer on mmenu-link: {"cursor: pointer" in css and ".mmenu-link" in css}')
    print(f'  90vw mobile cards: {"90vw" in css}')
    print(f'  contact-section-mobile-full: {"contact-section-mobile-full" in css}')
    if css_file == 'pages.css':
        print(f'  rp-hero styles: {"rp-hero" in css}')
