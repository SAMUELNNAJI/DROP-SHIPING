#!/usr/bin/env python3
"""Fix all 7 HTML pages: desktop nav + mobile menus."""
import re, os

BASE = r'c:\Users\ADMIN\Desktop\DROP SHIPING'
os.chdir(BASE)


def replace_in_file(fname, old, new):
    fpath = os.path.join(BASE, fname)
    with open(fpath, encoding='utf-8') as f:
        txt = f.read()
    if old in txt:
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(txt.replace(old, new))
        return True
    return False


# ============================================================
# DESKTOP NAV — remove <a> with Sell or Top Rated text
# ============================================================
for fname in ['shop.html', 'blog.html', 'refund-policy.html',
              'help.html', 'contact.html']:
    fpath = os.path.join(BASE, fname)
    with open(fpath, encoding='utf-8') as f:
        txt = f.read()
    lines = txt.split('\n')
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if ('>Sell<' in stripped or '>Top Rated<' in stripped) and 'href=' in stripped:
            continue  # skip this line
        new_lines.append(line)
    # Clean up empty lines in nav area
    txt = '\n'.join(new_lines)
    txt = re.sub(r'\n{3,}', '\n\n', txt)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(txt)
    print(f'{fname}: desktop nav cleaned')

print('Desktop nav fixes done.')


# ============================================================
# MOBILE MENU — all pages get the same 5-link menu
# (Shop, How It Works, About, Blog, Contact)
# ============================================================
ABOUT_MENU = (
    '       <nav class="mmenu-nav">\n'
    '         <a class="mmenu-link" href="shop.html" style="--i:0">\n'
    '           <span class="mmenu-num">01</span> Shop\n'
    '           <svg class="mmenu-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"/><polyline points="13 5 20 12 13 19"/></svg>\n'
    '         </a>\n'
    '         <a class="mmenu-link" href="index.html#safe" style="--i:1">\n'
    '           <span class="mmenu-num">02</span> How It Works\n'
    '           <svg class="mmenu-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"/><polyline points="13 5 20 12 13 19"/></svg>\n'
    '         </a>\n'
    '         <a class="mmenu-link" href="about.html" style="--i:2">\n'
    '           <span class="mmenu-num">03</span> About\n'
    '           <svg class="mmenu-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"/><polyline points="13 5 20 12 13 19"/></svg>\n'
    '         </a>\n'
    '         <a class="mmenu-link" href="blog.html" style="--i:3">\n'
    '           <span class="mmenu-num">04</span> Blog\n'
    '           <svg class="mmenu-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"/><polyline points="13 5 20 12 13 19"/></svg>\n'
    '         </a>\n'
    '         <a class="mmenu-link" href="contact.html" style="--i:4">\n'
    '           <span class="mmenu-num">05</span> Contact\n'
    '           <svg class="mmenu-arrow" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="12" x2="20" y2="12"/><polyline points="13 5 20 12 13 19"/></svg>\n'
    '         </a>\n'
    '       </nav>'
)

for fname, active_href, active_label in [
    ('shop.html', 'shop.html', 'Shop'),
    ('blog.html', 'blog.html', 'Blog'),
    ('contact.html', 'contact.html', 'Contact'),
    ('refund-policy.html', 'refund-policy.html', 'Refund Policy'),
    ('help.html', 'help.html', 'Help Center'),
]:
    fpath = os.path.join(BASE, fname)
    with open(fpath, encoding='utf-8') as f:
        txt = f.read()

    # Build the custom menu for this page
    menu = ABOUT_MENU
    # Make the active page highlighted
    menu = menu.replace(
        f'href="{active_href}"',
        f'href="{active_href}" class="mmenu-link--active"',
        1
    )
    if active_label != 'Contact':
        menu = menu.replace('>Contact<', f'>{active_label}<', 1)

    # Replace old mmenu-nav
    old_m = re.search(r'<nav class="mmenu-nav">.*?</nav>', txt, re.DOTALL)
    if old_m:
        txt = txt.replace(old_m.group(0), menu)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(txt)
        print(f'{fname}: mobile menu replaced')
    else:
        print(f'{fname}: mmenu-nav NOT FOUND')

print('Mobile menu fixes done.')
