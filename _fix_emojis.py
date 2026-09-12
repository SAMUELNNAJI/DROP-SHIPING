#!/usr/bin/env python3
"""Replace emoji icons with SVGs in shop.html drawer."""
import os
os.chdir('c:/Users/ADMIN/Desktop/DROP SHIPING')

with open('shop.html', 'r', encoding='utf-8', errors='replace') as f:
    shop = f.read()

emoji_to_svg = {
    '🛍️': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2L2 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-4-4z"/><path d="M16 10a4 4 0 01-8 0"/></svg>',
    '📱': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>',
    '👗': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.38 3.46L16 2a4 4 0 01-8 0L3.62 3.46a2 2 0 00-1.34 2.23l.58 3.47a1 1 0 00.99 1.06l3.81-.94a4 4 0 013.53 3.4l.21 2.54a2 2 0 001.78 1.78l2.54.21a4 4 0 013.4 3.53l-.94 3.81a1 1 0 001.06.99l3.47.58a2 2 0 002.23-1.34z"/><path d="M12 13l-2 3H8l4-5z"/></svg>',
    '🏠': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>',
    '🍳': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6h12l2 5H4l2-5z"/><path d="M12 13v8"/><path d="M8 21h8"/><path d="M4 21h16"/></svg>',
    '🪑': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>',
    '⌚': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>',
    '🎧': '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1F64FF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0118 0v6"/><path d="M21 19a2 2 0 01-2 2h-1a2 2 0 01-2-2v-3a2 2 0 012-2h3zM3 19a2 2 0 002 2h1a2 2 0 002-2v-3a2 2 0 00-2-2H3z"/></svg>',
}

count = 0
for emoji, svg in emoji_to_svg.items():
    c = shop.count(emoji)
    if c > 0:
        shop = shop.replace(emoji, svg)
        count += c
        print(f'Replaced {c}x {emoji}')

with open('shop.html', 'w', encoding='utf-8') as f:
    f.write(shop)
print(f'Total: {count} emoji replacements in shop.html')

# Also fix contact.html mobile-full class
with open('contact.html', 'r', encoding='utf-8', errors='replace') as f:
    contact = f.read()
if 'contact-section-mobile-full' not in contact:
    contact = contact.replace(
        '<section class="contact-section bg-gray">',
        '<section class="contact-section bg-gray contact-section-mobile-full">')
    with open('contact.html', 'w', encoding='utf-8') as f:
        f.write(contact)
    print('contact.html: mobile-full class added')

# Add 90vw + contact-section-mobile-full CSS to style.css
with open('style.css', 'r', encoding='utf-8', errors='replace') as f:
    css = f.read()
if 'contact-section-mobile-full' not in css:
    css += '''
/* Mobile: full-width cards at least 90vw */
@media (max-width: 640px) {
  .ip-card, .about-card, .blog-card, .seller-card, .b-card,
  .contact-form-card, .contact-office-card, .help-card, .feature-card,
  .about-value, .refund-card, .rp-card {
    min-width: 90vw;
    margin-left: auto;
    margin-right: auto;
  }
  .contact-section-mobile-full {
    grid-column: 1 / -1;
    width: 100% !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
  }
}
'''
    with open('style.css', 'w', encoding='utf-8') as f:
        f.write(css)
    print('style.css: 90vw + contact-section-mobile-full CSS added')

print('Done!')
