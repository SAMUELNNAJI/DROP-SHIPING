import re, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
pages = ['index.html','shop.html','about.html','blog.html','contact.html','help.html','refund-policy.html']
for f in pages:
    t = open(f, encoding='utf-8').read()
    has_sell = bool(re.search(r'>\s*Sell\s*<', t))
    has_toprated = 'Top Rated' in t
    navlinks = re.findall(r'<a[^>]*href=["\']([^"\']*)["\'][^>]*class=["\'][^"\']*nav-link', t)
    print(f, '| Sell:', has_sell, '| TopRated:', has_toprated)
    print('   navlinks:', navlinks)
