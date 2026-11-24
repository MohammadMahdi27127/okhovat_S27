"""Validate storage/configuration and apply migrations before opening the HTTP port."""
import os
import sys
import time
from pathlib import Path
from tempfile import NamedTemporaryFile

sys.path.insert(0, "/app/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main():
    import django
    django.setup()
    from django.conf import settings
    from django.core.management import call_command
    from django.db import connection, OperationalError, InterfaceError

    storage_dirs = {
        "AVATARS_DIR": Path(settings.AVATARS_DIR),
        "POSTS_DIR": Path(settings.POSTS_DIR),
        "SKILLS_DIR": Path(settings.SKILLS_DIR),
        # Legacy directory is retained for downloads of files uploaded before this release.
        "UPLOADS_DIR (legacy)": Path(settings.MEDIA_ROOT),
    }
    for label, directory in storage_dirs.items():
        directory.mkdir(parents=True, exist_ok=True)
        try:
            with NamedTemporaryFile(prefix=".write-check-", dir=directory):
                pass
        except OSError:
            raise SystemExit(
                f"{label} is not writable: {directory}. "
                "Mount a persistent disk writable by UID/GID 10001."
            )

    for attempt in range(1, 7):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            break
        except (OperationalError, InterfaceError):
            connection.close()
            print(f"PostgreSQL is not reachable yet ({attempt}/6). Check DATABASE_URL and private network access.", flush=True)
            if attempt == 6:
                raise SystemExit("PostgreSQL connection failed; no credentials have been printed.")
            time.sleep(2)

    # A session-level PostgreSQL advisory lock serializes overlapping deploys.
    # It does not replace the documented one-replica deployment requirement.
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [27527001])
        locked = cursor.fetchone()[0]
        for _ in range(45):
            if locked:
                break
            time.sleep(2)
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [27527001])
            locked = cursor.fetchone()[0]
        if not locked:
            raise SystemExit("Another deployment is migrating this database; retry when it finishes.")
    try:
        call_command("migrate", interactive=False)
    finally:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s)", [27527001])
    call_command("collectstatic", interactive=False, verbosity=0)
    call_command("check")
    connection.close()
    print("Initialization complete. Starting local Redis and the web service.", flush=True)


if __name__ == "__main__":
    main()
