#!/usr/bin/env bash
# Render build script (see render.yaml).
# Runs on every deploy, before the new version of the site goes live.
set -o errexit   # stop the build on the first failure
set -o pipefail  # surface errors from piped commands

echo "==> Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Serverless Postgres poolers can occasionally close a TLS connection while a
# deploy is starting.  Django migrations are idempotent, so retrying the whole
# command is safe and prevents a brief network blip from failing the deploy.
run_with_retry() {
  local label="$1"
  shift
  local attempt=1
  local max_attempts=4
  local delay=2

  until "$@"; do
    if (( attempt >= max_attempts )); then
      echo "==> ${label} failed after ${attempt} attempts."
      return 1
    fi
    echo "==> ${label} failed (attempt ${attempt}/${max_attempts}); retrying in ${delay}s..."
    sleep "$delay"
    attempt=$((attempt + 1))
    delay=$((delay * 2))
  done
}

echo "==> Collecting static files (served by WhiteNoise)"
python manage.py collectstatic --noinput

echo "==> Applying database migrations"
run_with_retry "Database migrations" python manage.py migrate --noinput

echo "==> Creating deployment superuser when configured"
run_with_retry "Deployment superuser setup" python manage.py bootstrap_superuser

echo "==> Build finished"
