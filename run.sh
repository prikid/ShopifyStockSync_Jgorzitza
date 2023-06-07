#!/bin/sh

python manage.py collectstatic --no-input
python manage.py migrate --noinput
gunicorn --config gunicorn-cfg.py app.wsgi
