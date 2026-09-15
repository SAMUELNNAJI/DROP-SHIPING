#!/usr/bin/env bash
# Render build script (see render.yaml).
# Runs on every deploy, before the new version of the site goes live.
set -o errexit   # stop the build on the first failure
set -o pipefail  # surface errors from piped commands

echo "==> Installing Python dependencies"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "==> Collecting static files (served by WhiteNoise)"
python manage.py collectstatic --noinput

echo "==> Applying database migrations"
python manage.py migrate --noinput

echo "==> Build finished"