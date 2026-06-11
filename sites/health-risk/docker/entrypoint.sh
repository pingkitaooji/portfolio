#!/bin/sh
set -e

if [ -n "$POSTGRES_HOST" ]; then
  echo "Waiting for PostgreSQL at $POSTGRES_HOST:$POSTGRES_PORT..."
  until nc -z "$POSTGRES_HOST" "${POSTGRES_PORT:-5432}"; do
    sleep 1
  done
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py shell --interface python -c "
from django.contrib.auth import get_user_model
User = get_user_model()
username = '$DJANGO_SUPERUSER_USERNAME'
email = '$DJANGO_SUPERUSER_EMAIL'
password = '$DJANGO_SUPERUSER_PASSWORD'
user, _ = User.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True})
user.email = email
user.is_staff = True
user.is_superuser = True
user.set_password(password)
user.save()
print(f'Superuser ready: {username}')
"
fi

if [ "${CREATE_DEMO_USERS:-1}" = "1" ]; then
  python manage.py shell --interface python -c "
from django.contrib.auth import get_user_model
User = get_user_model()
accounts = [
    ('hospital_a', 'hospital_a@example.com', 'demo123'),
    ('hospital_b', 'hospital_b@example.com', 'demo123'),
    ('hospital_c', 'hospital_c@example.com', 'demo123'),
]
for username, email, password in accounts:
    user, _ = User.objects.get_or_create(username=username, defaults={'email': email})
    user.email = email
    user.is_staff = False
    user.is_superuser = False
    user.set_password(password)
    user.save()
    print(f'Hospital user ready: {username}')
"
fi

exec "$@"
