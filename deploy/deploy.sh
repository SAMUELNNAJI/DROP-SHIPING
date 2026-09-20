#!/usr/bin/env bash
# VPS update script — the safe, repeatable way to ship new code.
#
#   cd /opt/drophub && bash deploy/deploy.sh
#
# It pulls the latest main, reuses build.sh (dependencies, collectstatic,
# migrations, superuser bootstrap) and restarts the systemd service.
set -o errexit   # stop on the first failure
set -o pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME=drophub

cd "$APP_DIR"

echo "==> Pulling the latest code"
git pull --ff-only

# First run on a fresh box: create the virtualenv before build.sh needs it.
if [ ! -x venv/bin/python ]; then
  echo "==> Creating the virtualenv (first run on this machine)"
  python3 -m venv venv
fi

# build.sh = pip install + collectstatic + migrate + bootstrap_superuser
# (the exact same steps Render runs on every deploy).
source venv/bin/activate
bash build.sh

echo "==> Restarting the $SERVICE_NAME service"
sudo systemctl restart "$SERVICE_NAME"
sleep 2

if systemctl is-active --quiet "$SERVICE_NAME"; then
  echo "==> $SERVICE_NAME is active — deploy finished."
else
  echo "!! $SERVICE_NAME did not come back up. Check: journalctl -u $SERVICE_NAME -n 50"
  exit 1
fi
