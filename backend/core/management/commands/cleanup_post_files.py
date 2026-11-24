from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import File
from core.storage import delete_file_and_release_quota


class Command(BaseCommand):
    help = "Delete post attachments older than the retention period while keeping post text and metadata."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7, help="Keep post files for this many days (default: 7).")
        parser.add_argument("--dry-run", action="store_true", help="Only report how many files would be deleted.")

    def handle(self, *args, **options):
        days = options["days"]
        if days < 1:
            self.stderr.write(self.style.ERROR("--days must be at least 1"))
            return
        cutoff = timezone.now() - timedelta(days=days)
        files = File.objects.filter(purpose="post", uploaded_at__lt=cutoff).order_by("uploaded_at")
        count = files.count()
        if options["dry_run"]:
            self.stdout.write(f"Would delete {count} post attachment(s) older than {days} day(s).")
            return
        deleted = 0
        for file_id in files.values_list("pk", flat=True).iterator(chunk_size=200):
            if delete_file_and_release_quota(file_id):
                deleted += 1
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {deleted} post attachment(s) older than {days} day(s). Post records were preserved."
        ))
