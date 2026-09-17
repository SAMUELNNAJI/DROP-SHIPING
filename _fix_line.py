import re

p = r'C:\Users\ADMIN\Desktop\DROP SHIPING\templates\checkout-payment.html'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the pay button line indentation
content = re.sub(
    r'^\s+Pay <span class="ck-currency" data-usd="626.23">\$626.23</span>',
    '            Pay <span class="ck-currency" data-usd="626.23">$626.23</span>',
    content,
    flags=re.MULTILINE
)

with open(p, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed pay button indentation')
