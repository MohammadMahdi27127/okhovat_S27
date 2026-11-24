#!/bin/sh
set -eu
umask 027
cd /app/backend

# One-off jobs use the same image without starting the web/cache processes.
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

python /app/deploy/prepare.py
exec /usr/bin/supervisord -c /app/deploy/supervisord.conf
