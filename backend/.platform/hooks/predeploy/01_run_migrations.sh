#!/bin/bash
set -euo pipefail

cd /var/app/current
/var/app/venv/*/bin/python manage.py migrate --noinput
