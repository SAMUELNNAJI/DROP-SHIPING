#!/usr/bin/env python3
"""Fix remaining issues: index cart, index emojis, contact layout, refund hero, cursor."""
import os, re

BASE = r'c:\Users\ADMIN\Desktop\DROP SHIPING'
os.chdir(BASE)

def rf(name):
    with open(os.path.join(BASE, name), 'rb') as f:
        return f.read().decode('utf-8', errors='replace')

def wf(name, content):
    with open(os.path.join(BASE, name), 'wb') as f:
        f.write(content.encode('utf-8'))


# 1. index.html: replace cart link with Contact in mobile menu
t = rf('index.html')
t = t.replace(
    '<a class="mmenu-link mmenu-link--cart" href="#" style="--i:4">',
    '<a class="mmenu-link" href="contact.html" style="--i:4">')
t = re.sub(
    r'<span class="mmenu-num mmenu-num--cart">.*?</span>\s*My Cart\s*<span class="mmenu-cart-count">.*?</span>',
    '<span class="mmenu-num">05</span> Contact',
    t, flags=re.DOTALL)
wf('index.html', t)
print('index.html: cart link -> Contact')

# 2. index.html: replace emoji category icons with SVG
svgs = {
    '🔍': '<svg class="search-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>',
    '💰': '<svg class="bag-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L2 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-4-4z"/><line x1="2" y1="6" x2="22" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>',
    '💻': '<svg class="tech-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    '👕': '<svg class="fashion-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.38 3.46L16 2a4 4 0 01-8 0L3.62 3.46a2 2 0 00-1.34 2.23l.58 3.47a1 1 0 00.99 1.06l3.81-.94a4 4 0 013.53 3.4l.21 2.54a2 2 0 001.78 1.78l2.54.21a4 4 0 013.4 3.53l-.94 3.81a1 1 0 001.06.99l3.47.58a2 2 0 002.23-1.34z"/><path d="M12 13l-2 3H8l4-5z"/></svg>',
    '🏠': '<svg class="home-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    '💄': '<svg class="beauty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6h12l2 5H4l2-5z"/><path d="M12 13v8"/><path d="M8 21h8"/><path d="M4 21h16"/></svg>',
    '🎒': '<svg class="travel-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2h14a2 2 0 002-2z"/><path d="M21 10l-4 4-5-5-3 3"/></svg>',
    '📚': '<svg class="hobby-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>',
    '🛋️': '<svg class="sports-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
}
n = 0
for emoji, svg in svgs.items():
    if emoji in t:
        t = t.replace(emoji, svg)
        n += 1
wf('index.html', t)
print(f'index.html: {n} emoji icons -> SVG')

# 3. contact.html: mobile-full class
ct = rf('contact.html')
ct = ct.replace('<section class="contact-section bg-gray">',
                '<section class="contact-section bg-gray contact-section-mobile-full">')
wf('contact.html', ct)
print('contact.html: mobile-full class added')

# 4. refund-policy.html: rp-hero class
rt = rf('refund-policy.html')
rt = rt.replace('<div class="hero-wrapper">',
                '<div class="hero-wrapper rp-hero">', 1)
wf('refund-policy.html', rt)
print('refund-policy.html: rp-hero class added')

# 5. style.css: cursor:pointer
cs = rf('style.css')
if '.mmenu-link {' not in cs and '.mmenu-link:hover' in cs:
    cs = cs.replace(
        '.mmenu-link:hover { background: rgba(31,100,255,.07); color: #1F64FF; }',
        '.mmenu-link { cursor: pointer; }\n.mmenu-link:hover { background: rgba(31,100,255,.07); color: #1F64FF; }')
    wf('style.css', cs)
    print('style.css: cursor:pointer added to mmenu-link')
else:
    print('style.css: cursor already present')

print('\nAll done.')

cat_svgs = {
    '🔍': '<svg class="search-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.5" y2="16.5"/></svg>',
    '💰': '<svg class="bag-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L2 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-4-4z"/><line x1="2" y1="6" x2="22" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>',
    '💻': '<svg class="tech-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    '👕': '<svg class="fashion-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.38 3.46L16 2a4 4 0 01-8 0L3.62 3.46a2 2 0 00-1.34 2.23l.58 3.47a1 1 0 00.99 1.06l3.81-.94a4 4 0 013.53 3.4l.21 2.54a2 2 0 001.78 1.78l2.54.21a4 4 0 013.4 3.53l-.94 3.81a1 1 0 001.06.99l3.47.58a2 2 0 002.23-1.34z"/><path d="M12 13l-2 3H8l4-5z"/></svg>',
    '🏠': '<svg class="home-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    '💄': '<svg class="beauty-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6h12l2 5H4l2-5z"/><path d="M12 13v8"/><path d="M8 21h8"/><path d="M4 21h16"/></svg>',
    '🎒': '<svg class="travel-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 16V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2h14a2 2 0 002-2z"/><path d="M21 10l-4 4-5-5-3 3"/></svg>',
    '📚': '<svg class="hobby-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>',
    '🛋️': '<svg class="sports-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
}

# SVG definitions (shared across files)
svg_map = {
