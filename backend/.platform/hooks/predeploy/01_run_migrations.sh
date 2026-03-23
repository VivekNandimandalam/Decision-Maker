#!/bin/bash
set -euo pipefail

cd /var/app/staging
/var/app/venv/*/bin/python manage.py migrate --noinput
