#!/usr/bin/env bash
# Render build step for the API service.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py ensure_superadmin
