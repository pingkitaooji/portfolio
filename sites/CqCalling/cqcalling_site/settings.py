import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("CQCALLING_SECRET_KEY", "django-insecure-cqcalling-demo-key")
DEBUG = os.getenv("CQCALLING_DEBUG", "1") == "1"
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "CQCALLING_ALLOWED_HOSTS",
        "127.0.0.1,localhost,cqcalling.yourdomain.com",
    ).split(",")
    if host.strip()
]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "cqcalling_site.urls"
WSGI_APPLICATION = "cqcalling_site.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {},
    },
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

LANGUAGE_CODE = "zh-hant"
TIME_ZONE = "Asia/Taipei"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
