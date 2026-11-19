import logging
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

import django

django.setup()

from django.core.management import call_command
from django.db import connection

logger = logging.getLogger(__name__)
MIGRATION_LOCK_KEY = (1313161299, 1162699079)


def main():
    if connection.vendor != "postgresql":
        call_command("migrate", interactive=False)
        return

    logger.info("Waiting for the startup migration lock.")
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_lock(%s, %s)", MIGRATION_LOCK_KEY)
    try:
        logger.info("Running Django migrations.")
        call_command("migrate", interactive=False)
    finally:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT pg_advisory_unlock(%s, %s)",
                MIGRATION_LOCK_KEY,
            )
            released = cursor.fetchone()[0]
        if not released:
            raise RuntimeError("The startup migration lock was not held.")
        logger.info("Released the startup migration lock.")


if __name__ == "__main__":
    main()
