cart_in_menu_pattern = re.compile(
    r'\s*<a class="mmenu-link mmenu-link--cart"[^>]*>.*?</a>\n',
    re.DOTALL
)

for fname in ['shop.html', 'blog.html', 'refund-policy.html',
              'help.html', 'contact.html', 'about.html', 'index.html']:
    txt = read_file(os.path.join(BASE, fname))
    if 'mmenu-link--cart' in txt:
        txt = cart_in_menu_pattern.sub('', txt)
        write_file(os.path.join(BASE, fname), txt)
        print(f'{fname}: cart removed from mobile menu')