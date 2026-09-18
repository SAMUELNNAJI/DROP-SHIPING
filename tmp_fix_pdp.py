import pathlib
p = pathlib.Path("templates/product_detail.html")
t = p.read_text(encoding="utf-8")
old1 = 'data-img="{{ product.image_src }}">'
assert t.count(old1) == 1, t.count(old1)
new1 = 'data-img="{{ product.image_src }}" data-role-blocked="{% if viewer_state == \'seller\' or viewer_state == \'admin\' %}1{% endif %}" data-role-kind="{{ viewer_state|default:\'guest\' }}">'
t = t.replace(old1, new1)
old2 = '<a href="/checkout/" class="pdp-buy-now-btn">Buy now</a>'
assert t.count(old2) == 1, t.count(old2)
new2 = '<a href="/checkout/" class="pdp-buy-now-btn" data-role-blocked="{% if viewer_state == \'seller\' or viewer_state == \'admin\' %}1{% endif %}" data-role-kind="{{ viewer_state|default:\'guest\' }}">Buy now</a>'
t = t.replace(old2, new2)
p.write_text(t, encoding="utf-8")
print("PDP_ATTRS_OK")
