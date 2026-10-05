#!/usr/bin/env python
"""Run Django commands with the environment selected in settings/.env."""

import os
import sys


def main() -> None:
    from settings.conf import get_settings_module

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", get_settings_module())
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
