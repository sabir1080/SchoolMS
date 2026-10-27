#!/usr/bin/env bash
# Render build step for the API service.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py ensure_superadmin
# One-time demo reset: runs only when SEED_DEMO_COMMIT is set to exactly this deploy's commit,
# so it can never run again on a later deploy.
if [ -n "$SEED_DEMO_COMMIT" ] && [ "$SEED_DEMO_COMMIT" = "$RENDER_GIT_COMMIT" ]; then
  python manage.py seed_demo
fi
