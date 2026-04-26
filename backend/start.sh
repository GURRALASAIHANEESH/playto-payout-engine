#!/usr/bin/env bash
set -o errexit

python manage.py migrate
python manage.py seed_data
gunicorn playto.wsgi:application --bind 0.0.0.0:$PORT