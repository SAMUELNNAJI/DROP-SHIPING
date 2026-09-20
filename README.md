# DropHub — Dropshipping Marketplace (Django)

Your static dropshipping storefront, now running on Django.

## Project structure

- `dropshipping/` — Django project (settings, root URL configuration)
- `shop/` — the store app (pages are served from `shop/views.py`)
- `accounts/` — custom user model + sign up / sign in / sign out
- `dashboards/` — buyer, seller and admin dashboards + seller verification uploads
- `templates/` — all 12 HTML pages (index, shop, checkout, …) plus the dashboard/auth layouts
- `static/` — CSS, JS (`cart.js`), `Logo.png`, and product images (`static/img/`)
- `db.sqlite3` — SQLite database used for local development only
- `venv/` — Python virtual environment (Django lives here)
- `requirements.txt` — production dependencies (installed on Render)
- `build.sh` + `render.yaml` — Render deploy configuration
- `.env.example` — template for environment variables (copy it to `.env`)

## Getting started

```powershell
# 1. Activate the virtual environment
.\venv\Scripts\Activate.ps1

# 2. Install/refresh dependencies (includes the production packages)
pip install -r requirements.txt

# 3. Create your local env file (first time only; `.env` is git-ignored)
Copy-Item .env.example .env

# 4. Run the development server
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

Locally the project keeps using `db.sqlite3` and `DEBUG=True`; the `.env` file
only sets `DEBUG=True` so that `runserver` works exactly as before.

> **If `pip install` hangs or times out:** this network blocks
> `files.pythonhosted.org` (the host PyPI serves wheels from), while `pypi.org`
> itself is reachable. Install through a mirror instead — for example:
> `pip install -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/`
> This only affects your machine; Render downloads normally from PyPI.


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

---

# Deploying to Render

Everything needed for Render is already in the repo:

| File | Purpose |
|---|---|
| `render.yaml` | Blueprint: web service, build/start commands, env vars |
| `build.sh` | Installs deps, runs `collectstatic`, runs `migrate` on every deploy |
| `requirements.txt` | Pinned production dependencies (Django, gunicorn, psycopg, whitenoise, dj-database-url) |
| `.python-version` | Pins Python 3.14.3 (Render's current default) |
| `.gitattributes` | Forces LF line endings for `build.sh` |
| `.env.example` | Documents every supported environment variable |

`dropshipping/settings.py` reads all of its configuration from environment
variables, so nothing secret is committed:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | **Yes** | Neon Postgres connection string (see below) |
| `SECRET_KEY` | **Yes** | Blueprint generates it for you |
| `DEBUG` | No | `False` on Render, `True` locally. A `DEBUG` entry in `.env` is ignored on Render |
| `DJANGO_ALLOWED_HOSTS` | No | Render's own hostname is added automatically |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Only for custom domains | `https://*.onrender.com` is allowed automatically |
| `DB_CONN_MAX_AGE` | No | Defaults to `0`, correct for Neon's pooler |
| `WEB_CONCURRENCY` | No | Ignored: Gunicorn is started with explicit worker flags |
| `EMAIL_*` | No | Same optional features as before |
| `DJANGO_EMAIL_BACKEND` | No | Override the mail backend (console by default, SMTP once `EMAIL_HOST` is set) |
| `MEDIA_ROOT`, `SERVE_MEDIA` | No | Media handling, see "Uploaded files" |

## 1. Database (Neon Postgres)

Use the pooled connection string (the host containing `-pooler`) with
`sslmode=require&channel_binding=require`, for example:

```
postgresql://neondb_owner:********@ep-lively-river-b1b6dzqd-pooler.c-5.eu-central-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

Django is configured with `DISABLE_SERVER_SIDE_CURSORS = True`, which is the
recommended setting for PgBouncer-style poolers such as Neon's pooled endpoint.

## 2. Push the repo, create the Blueprint

```powershell
git add .
git commit -m "Prepare for Render deployment"
git push origin main
```

Then in the Render Dashboard: **New → Blueprint → select this repo**. Render
reads `render.yaml`, creates the `drophub` web service in Frankfurt (closest
region to the Neon database) and asks for the one value it cannot generate:

- `DATABASE_URL` → paste the Neon connection string.

Deploys after that run automatically on every push to `main`.

> **Custom domains and health checks.** Render probes `GET /` every few seconds
> and counts any **2xx or 3xx** response as healthy, so the automatic
> `http → https` redirect is fine. But once a custom domain is verified, Render
> sends that domain in the probe's `Host` header — add it to
> `DJANGO_ALLOWED_HOSTS` (and `DJANGO_CSRF_TRUSTED_ORIGINS`), otherwise Django
> answers `400` and the instance is reported as unhealthy.

### Manual setup instead of the Blueprint

| Setting | Value |
|---|---|
| Runtime / Language | Python |
| Build Command | `bash build.sh` |
| Start Command | `gunicorn dropshipping.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --threads 4 --access-logfile - --error-logfile -` |
| Health Check Path | `/` (optional — any 2xx *or* 3xx counts as healthy) |

…plus the environment variables from the table above (`DATABASE_URL`,
`SECRET_KEY=generate`, `DEBUG=false`).

## 3. First-run tasks (once, after the first successful deploy)

The build already runs `migrate`, so the schema exists. Create your admin user:

```bash
# Render Dashboard -> Shell (paid plans) or run locally with the production env:
DATABASE_URL="postgresql://…neon.tech/neondb?sslmode=require&channel_binding=require" \
  python manage.py createsuperuser
```

On the free plan there is no Shell tab, so run the command above from your
machine (or from a one-off job) with `DATABASE_URL` exported. Admin lives at
`https://<your-service>.onrender.com/admin/`.

### Optional: copy your existing SQLite data

```powershell
# Dump from the local SQLite database …
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.permission -e admin.logentry --indent 2 > data.json

# … then load it into Neon (PowerShell needs the env var set for the session):
$env:DATABASE_URL = "postgresql://…neon.tech/neondb?sslmode=require&channel_binding=require"
python manage.py loaddata data.json
Remove-Item Env:\DATABASE_URL
```

## Static files, uploaded files and email

- **Static files** (CSS/JS/images) are collected into `staticfiles/` at build
  time and served by **WhiteNoise** — no extra config needed.
- **Uploaded files** (seller verification documents) are stored on the service's
  disk, which Render **wipes on every deploy** (free instances also spin down
  when idle). They are served by Django from `/media/`. For durable uploads,
  either attach a Render persistent disk and set `MEDIA_ROOT=/var/data/media`
  (paid plans only), or move media to object storage (S3/Cloudinary) and set
  `SERVE_MEDIA=false`.
- **Email**: without `EMAIL_HOST` set, messages are written to the Render logs
  (`DJANGO_EMAIL_BACKEND` overrides the backend). Note that Render's *free* web
  services block outbound SMTP on ports 25/465/587 — use an HTTPS email API
  (e.g. Resend/Postmark) or a paid instance if you need real mail. Until a real
  provider is configured, `manage.py check --deploy` reports `mail.E001`; that is
  expected and does not affect deploys, because the build runs `migrate` (and
  `collectstatic`), which skip deploy-only checks.

## Production checklist

- [x] `DEBUG=False` (automatic on Render via `RENDER=true`)
- [x] `SECRET_KEY` generated by Render
- [x] `SECURE_SSL_REDIRECT`, secure cookies and `SECURE_PROXY_SSL_HEADER` enabled
      (automatically applied whenever `DEBUG` is off)
- [x] `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS` filled in from the Render hostname
- [ ] Point a custom domain and add it to `DJANGO_ALLOWED_HOSTS` +
      `DJANGO_CSRF_TRUSTED_ORIGINS`
- [ ] Optionally set `SECURE_HSTS_SECONDS=31536000` once the domain is stable

---

# Deploying to your own VPS (Ubuntu + Nginx + Gunicorn)

Prefer to self-host? The same app runs on any Ubuntu VPS with no code changes —
`dropshipping/settings.py` is fully environment-driven. A complete step-by-step
guide (server prep, Postgres, systemd, Nginx, HTTPS via Certbot, backups,
updates) lives in **`DEPLOY_VPS.md`**:

| File | Purpose |
|---|---|
| `DEPLOY_VPS.md` | Step-by-step VPS deployment guide |
| `deploy/env.vps.example` | Production `.env` template for a VPS |
| `deploy/drophub.service` | systemd unit that runs Gunicorn on 127.0.0.1:8000 |
| `deploy/nginx-drophub.conf` | Nginx site: static/media serving + reverse proxy |
| `deploy/deploy.sh` | One-command future deploys (`git pull` + `build.sh` + restart) |

After switching your domain's traffic to the VPS, pause the Render service so
only one front-end writes to the database.

