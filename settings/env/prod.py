"""Production requires PostgreSQL credentials and HTTPS."""

from settings.base import *  # noqa: F403
from settings.conf import config

DEBUG = False
DATABASE_CONNECTION_AGE = 60
HSTS_SECONDS = 31536000
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("BLOG_DB_NAME"),
        "USER": config("BLOG_DB_USER"),
        "PASSWORD": config("BLOG_DB_PASSWORD"),
        "HOST": config("BLOG_DB_HOST"),
        "PORT": config("BLOG_DB_PORT", default=5432, cast=int),
        "CONN_MAX_AGE": DATABASE_CONNECTION_AGE,
    }
}
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = HSTS_SECONDS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
