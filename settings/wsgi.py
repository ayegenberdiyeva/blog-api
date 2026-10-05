"""WSGI entry point using the same environment selection as manage.py."""

import os

from django.core.wsgi import get_wsgi_application

from settings.conf import get_settings_module

os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_settings_module())
application = get_wsgi_application()
