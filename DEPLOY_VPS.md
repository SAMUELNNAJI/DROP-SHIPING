# Deploying DropHub to your own VPS

Self-hosting on an **Ubuntu 22.04/24.04 LTS** server with the classic, boring,
reliable stack:

```
Browser ─> Nginx (port 80/443, TLS via Certbot)
              │  /static/  → /opt/drophub/staticfiles  (collected at build)
              │  /media/   → /opt/drophub/media       (uploads, persistent)
              └─  /        → Gunicorn 127.0.0.1:8000 (systemd service)
                                 └─ dropshipping.wsgi  → Postgres (local or Neon)
```

**No code changes are needed.** `dropshipping/settings.py` reads everything
from environment variables — the same app that runs on Render runs here; only
the environment (`.env`) and the surrounding services differ.

Everything you need is in the repo:

| File | Purpose |
|---|---|
| `DEPLOY_VPS.md` | This guide |
| `deploy/env.vps.example` | Production `.env` template — copy to `/opt/drophub/.env` |
| `deploy/drophub.service` | systemd service that runs Gunicorn |
| `deploy/nginx-drophub.conf` | Nginx reverse-proxy site (static, media, gzip) |
| `deploy/deploy.sh` | One-command future deploys (`git pull` + rebuild + restart) |

> Windows dev machine? Fine — `.gitattributes` forces LF line endings on all
> `*.sh`, so the scripts work straight from a `git clone` on the server.

---

## 0. What you need

- A VPS (Ubuntu 22.04/24.04) with root SSH access — 1 vCPU / 1 GB is plenty to start.
- A domain (e.g. `drophub.example.com`) whose **A** record (and **AAAA** if you
  use IPv6) points at the VPS IP. Add `www` as a second record or a CNAME.
- ~15 minutes.

---

## 1. Prepare the server

SSH in as root and install the system packages:

```bash
apt update && apt -y upgrade
apt -y install nginx postgresql python3-venv python3-pip git certbot python3-certbot-nginx ufw

# Firewall: SSH + web only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

Create an unprivileged user that owns/runs the app (it needs `sudo` only for
the `systemctl restart` inside `deploy.sh`):

```bash
adduser drophub
usermod -aG sudo drophub
mkdir -p /opt/drophub
chown drophub:drophub /opt/drophub
```

---

## 2. Create the database

**Option A — Postgres on this VPS (default, recommended):**

```bash
sudo -u postgres psql <<'SQL'
CREATE USER drophub WITH PASSWORD 'CHANGE-ME-DB-PASSWORD';
CREATE DATABASE drophub OWNER drophub;
SQL
```

Postgres only listens locally by default and the app connects via `localhost`,
so nothing is exposed to the internet.

**Option B — keep your existing Neon database:** skip this step and paste the
same pooled `DATABASE_URL` you use on Render into `.env` below. (Read
"Running alongside Render" in the notes at the end before you do this.)

---

## 3. Get the code + configure

```bash
sudo -u drophub -i
git clone https://github.com/SAMUELNNAJI/DROP-SHIPING.git /opt/drophub
cd /opt/drophub

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Production environment
cp deploy/env.vps.example .env
nano .env
```

In `.env`, replace every **CHANGE-ME**:

- `SECRET_KEY` → generate with
  `python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"`
- `DATABASE_URL` → your local Postgres credentials from step 2 (or the Neon URL).
- `DJANGO_ALLOWED_HOSTS` / `DJANGO_CSRF_TRUSTED_ORIGINS` → your real domain
  (`drophub.example.com,www.drophub.example.com`).
- Optionally the `DJANGO_SUPERUSER_*` trio so the build creates your admin.
- Payments/email/OAuth keys — copy them out of the Render dashboard.

Lock the file down:

```bash
chmod 600 .env
```

---

## 4. First build (migrate + static files)

```bash
cd /opt/drophub
source venv/bin/activate
bash build.sh          # pip install, collectstatic, migrate, superuser bootstrap
```

Sanity-check that the app boots in production mode:

```bash
DEBUG=false SECRET_KEY=x DJANGO_ALLOWED_HOSTS=localhost \
  python manage.py check --deploy
```

(Warnings about missing email config / HSTS are fine at this stage.)

---

## 5. Run it as a service (systemd)

```bash
sudo cp /opt/drophub/deploy/drophub.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now drophub

# Verify
systemctl status drophub --no-pager
curl -I http://127.0.0.1:8000/     # expect 200 (or 301 once SSL redirect is on)
```

Logs live in the journal: `journalctl -u drophub -f`.

---

## 6. Nginx in front

```bash
sudo cp /opt/drophub/deploy/nginx-drophub.conf /etc/nginx/sites-available/drophub
sudo nano /etc/nginx/sites-available/drophub   # set server_name to your domain
sudo ln -s /etc/nginx/sites-available/drophub /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default    # remove the placeholder site
sudo nginx -t && sudo systemctl reload nginx
```

Open `http://your-server-ip/` in a browser — the site should render.

---

## 7. HTTPS (free Let's Encrypt certificate)

```bash
sudo certbot --nginx -d drophub.example.com -d www.drophub.example.com
```

Certbot rewrites the Nginx config (adds the 443 server block and the
HTTP→HTTPS redirect) and auto-renews. Check renewal with
`sudo certbot renew --dry-run`.

Now turn on the Django-side HTTPS enforcement:

```bash
nano /opt/drophub/.env        # SECURE_SSL_REDIRECT=False  →  True
sudo systemctl restart drophub
# optional, once the domain is final (browsers remember HSTS for a year!):
# SECURE_HSTS_SECONDS=31536000
```

---

## 8. Point the payment providers at the new domain

- **Paystack** dashboard → Webhooks:
  `https://drophub.example.com/dashboards/checkout/paystack/webhook/`
- **PayPal**: go live with `PAYPAL_MODE=live`; the return/callback URLs are
  built from the incoming request automatically.
- **Pi Developer Portal**: update the app's endpoints to the new domain.

---

## 9. Every future deploy

```bash
cd /opt/drophub && bash deploy/deploy.sh
```

Pulls `main`, installs dependencies, collects static files, runs migrations,
bootstraps the superuser and restarts the service — the exact steps Render
performs, in one command (downtime ≈ 2 seconds).

---

## 10. Backups (set this up on day one)

Manual snapshot:

```bash
sudo -u postgres pg_dump -Fc drophub > /var/backups/drophub-$(date +%F).dump
tar -czf /var/backups/drophub-media-$(date +%F).tgz -C /opt/drophub media
```

Daily/weekly automation (`crontab -e` as root):

```
15 3 * * * sudo -u postgres pg_dump -Fc drophub > /var/backups/drophub-$(date +\%F).dump
30 3 * * 0 tar -czf /var/backups/drophub-media-$(date +\%F).tgz -C /opt/drophub media
```

Copy dumps off the server (S3, another machine — anything but the same disk).

---

## Troubleshooting

| Symptom | Where to look / fix |
|---|---|
| 502 Bad Gateway | Gunicorn down: `journalctl -u drophub -n 50`. Usually a bad `.env` value. |
| 400 DisallowedHost | Add the host to `DJANGO_ALLOWED_HOSTS` in `.env`, restart drophub. |
| CSRF error on login/checkout | Add `https://your-domain` to `DJANGO_CSRF_TRUSTED_ORIGINS`, restart. |
| CSS/JS 404 | `staticfiles/` missing or Nginx path wrong — rerun `bash build.sh`. |
| Redirects to https but cert invalid | Run the certbot step; keep `SECURE_SSL_REDIRECT=False` until it succeeds. |
| Email not sending | Set `EMAIL_HOST*`/ZeptoMail vars in `.env` (a VPS can send SMTP directly, unlike Render's free tier). |

Useful commands: `systemctl status drophub`, `journalctl -u drophub -f`,
`sudo tail -f /var/log/nginx/error.log`, `venv/bin/python manage.py check --deploy`.

---

## Notes

- **Running alongside Render:** both apps can point at the same `DATABASE_URL`
  without breaking, but only one should receive traffic — switch the domain's
  DNS to the VPS, watch it for a few days, then pause/delete the Render
  service. Don't leave two live front-ends writing to the same DB long-term.
- **Uploaded files** (`/opt/drophub/media`) persist on a VPS, unlike Render's
  ephemeral disk. Copy existing uploads across before the switch if you have
  any (download them from the site, upload to `/opt/drophub/media/`).
- **Updates:** `apt update && apt upgrade` monthly; `deploy.sh` handles the app.
  Consider `apt -y install unattended-upgrades fail2ban`.
- **Scaling later:** raise `--workers` in the systemd unit (2 × cores + 1 is
  the classic formula), or move media to S3/Cloudinary and set
  `SERVE_MEDIA=false`.


