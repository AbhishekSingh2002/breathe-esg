#!/bin/sh
python manage.py migrate --noinput
python manage.py seed_demo_user
gunicorn config.wsgi:application
