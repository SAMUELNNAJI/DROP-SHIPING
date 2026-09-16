# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.abspath("."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dropshipping.settings")
import django

django.setup()
from django.conf import settings

if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
u, _ = User.objects.get_or_create(username="sanity_seller", defaults={"role": "seller"})
u.role = "seller"
u.set_password("sanity-pass")
u.save()

c = Client()
c.post("/accounts/signin/", {"username": "sanity_seller", "password": "sanity-pass"})
r = c.get("/dashboards/seller/products/add/")
body = r.content.decode()
assert r.status_code == 200, r.status_code
assert "Unverified · posting allowed" in body, "unverified chip missing"
assert "verify your identity" in body.lower(), "unverified banner missing"
print("SANITY OK: unverified seller can open add-product page with notice")
