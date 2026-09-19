import os, re, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dropshipping.settings')
import django; django.setup()
from django.test import Client
from django.contrib.auth import get_user_model
from shop.models import Product
from dashboards.models import CartItem

User = get_user_model()
user = User.objects.filter(role='buyer', is_active=True).first()
prods = list(Product.objects.filter(status='live'))[:2]
A, B = prods[0], prods[1]

c = Client(SERVER_NAME='localhost')
c.force_login(user)

def sync(items):
    r = c.post('/dashboards/cart/sync/', json.dumps(items), content_type='application/json', HTTP_HOST='localhost')
    return r.status_code, json.loads(r.content)

# 1. Simulate stale DB cart: only product A qty 1 in DB, "localStorage" has B qty 2
CartItem.objects.filter(user=user).delete()
CartItem.objects.create(user=user, product=A, quantity=1)
print('1. stale DB cart (A x1), localStorage=[B x2]')
st, d = sync([{'product_pk': B.pk, 'quantity': 2}])
print('   ', st, d, '| changed:', d.get('changed'))
print('   DB now:', [(i.product.name, i.quantity) for i in CartItem.objects.filter(user=user)])

# 2. Render checkout page — must show B with correct server-rendered amounts
r = c.get('/checkout/', HTTP_HOST='localhost')
h = r.content.decode()
print('2. /checkout/ render:', r.status_code)
print('   shows B:', B.name in h, '| shows stale A:', A.name in h)
print('   subtotal rendered:', re.search(r'id="ckTotal">\$([0-9.]+)<', h).group(1), '(expect %.2f)' % (B.price * 2))

# 3. Quantity change on payment page
st, d = sync([{'product_pk': B.pk, 'quantity': 5}])
print('3. qty 2 -> 5:', st, d, '| DB:', [(i.product.name, i.quantity) for i in CartItem.objects.filter(user=user)])

# 4. Idempotent re-sync: nothing changed
st, d = sync([{'product_pk': B.pk, 'quantity': 5}])
print('4. re-sync same:', st, d, '| changed:', d.get('changed'))

# 5. Payment page renders the synced cart
r = c.get('/checkout-payment/', HTTP_HOST='localhost')
h = r.content.decode()
vals = re.findall(r'data-usd="([0-9.]+)"', h)
print('5. /checkout-payment/ render:', r.status_code)
print('   shows B:', B.name in h)
print('   data-usd:', vals[:6], '| expect total', round(float(B.price) * 5 * 1.03, 2))

