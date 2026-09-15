# DropHub — Dropshipping Marketplace (Django)

Your static dropshipping storefront, now running on Django.

## Project structure

- `dropshipping/` — Django project (settings, root URL configuration)
- `shop/` — the store app (pages are served from `shop/views.py`)
- `templates/` — all 12 HTML pages (index, shop, checkout, …)
- `static/` — CSS, JS (`cart.js`), `Logo.png`, and product images (`static/img/`)
- `db.sqlite3` — SQLite database (created by migrations)
- `venv/` — Python virtual environment (Django lives here)

## Getting started

```powershell
# 1. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 2. Run the development server
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

## Pages

| URL | Page |
|---|---|
| `/` | Home |
| `/shop/` | Shop |
| `/about/`, `/blog/`, `/contact/`, `/help/` | Content pages |
| `/payouts/`, `/refund-policy/` | Seller / policy pages |
| `/privacy/` | Privacy Policy |
| `/terms/` | Terms of Service |
| `/signin/` | Sign in |
| `/checkout/`, `/checkout-payment/`, `/checkout-success/` | Checkout flow |
| `/admin/` | Django admin |

## Notes

- Original page links (`shop.html`, etc.) were rewritten to the URLs above, and
  asset references (`style.css`, `Logo.png`, `img/...`, `cart.js`) now point to
  `/static/...` — the cart engine in `static/cart.js` was updated too.
- To install dependencies on a fresh machine: `pip install -r requirements.txt`
- Next steps for a real backend: add models for products/orders in `shop/models.py`,
  run `python manage.py makemigrations shop`, and build an admin at `/admin/`.
