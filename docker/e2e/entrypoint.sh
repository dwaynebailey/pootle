#!/bin/bash
#
# Phase 0, stream D: bring up a minimally-seeded instance for the
# Playwright smoke suite. Idempotent (guards on existence) so restarting
# the container doesn't re-seed. Not a production entrypoint.

set -e

echo "Waiting for postgres..."
for i in $(seq 1 30); do
    python2 -c "
import psycopg2, sys
try:
    psycopg2.connect(host='postgres', dbname='pootledb', user='pootle', password='CHANGEME')
except psycopg2.OperationalError:
    sys.exit(1)
" 2>/dev/null && break
    sleep 2
done

python2 manage.py migrate --noinput
python2 manage.py initdb

python2 manage.py shell -c "
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin', 'admin@example.com', 'e2e-admin-pw')
    print('created admin user')
else:
    u = User.objects.get(username='admin')
    print('admin user already exists')

# allauth blocks login behind email verification regardless of
# is_superuser - mark it verified directly rather than actually running
# the confirmation-email flow. Found running Phase 0 stream D.
EmailAddress.objects.get_or_create(
    user=u, email=u.email,
    defaults={'verified': True, 'primary': True})
"

exec python2 manage.py runserver 0.0.0.0:8000
