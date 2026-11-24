"""Purpose-aware private file storage and quota-safe deletion helpers."""
from pathlib import Path

from django.conf import settings
from django.db import transaction

from .models import File, UploadUsage

PURPOSE_DIRS = {
    "avatar": "AVATARS_DIR",
    "post": "POSTS_DIR",
    "proof": "SKILLS_DIR",
    "landing": "LANDING_DIR",
}


def storage_dir(purpose: str) -> Path:
    setting_name = PURPOSE_DIRS.get(purpose)
    if not setting_name:
        raise ValueError(f"Unsupported file purpose: {purpose}")
    return Path(getattr(settings, setting_name))


def file_path(item: File) -> Path:
    """New purpose-specific path, with legacy fallback for pre-migration files."""
    current = storage_dir(item.purpose) / item.id
    if current.is_file():
        return current
    legacy = Path(settings.MEDIA_ROOT) / item.id
    return legacy if legacy.is_file() else current


def delete_file_and_release_quota(item_or_id) -> bool:
    """Delete a file row, release its owner's quota, then unlink disk bytes.

    Legacy rows created before size tracking are charged using the actual file size
    (with the historical 4 KiB minimum) whenever the old file is still present.
    """
    file_id = item_or_id.pk if isinstance(item_or_id, File) else str(item_or_id)
    disk_paths = []
    with transaction.atomic():
        try:
            item = File.objects.select_for_update().get(pk=file_id)
        except File.DoesNotExist:
            return False
        path = file_path(item)
        actual_size = path.stat().st_size if path.is_file() else 0
        charge = item.quota_bytes or max(actual_size, 4096)
        usage = UploadUsage.objects.select_for_update().filter(actor_id=item.owner_id).first()
        if usage:
            usage.used = max(0, usage.used - charge)
            usage.save(update_fields=["used"])
        disk_paths = [storage_dir(item.purpose) / item.id, Path(settings.MEDIA_ROOT) / item.id]
        item.delete()
    for path in disk_paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            # The DB row is already gone; a later orphan-file cleanup can remove it.
            pass
    return True
