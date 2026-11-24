"""Import the previous PostgreSQL schema into a migrated, empty Django database.

The source connection is read-only. Account passwords remain hashes.
Sessions deliberately expire at cutover to prevent accepting old authentication.
"""
import os
import re
import psycopg
from psycopg.rows import dict_row
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core import models as m


def rewrite_urls(value):
    if isinstance(value, dict):
        return {key: rewrite_urls(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rewrite_urls(item) for item in value]
    if isinstance(value, str) and re.fullmatch(r"/api/files/[a-f0-9]{32}", value):
        return value + "/"
    return value


class Command(BaseCommand):
    help = "Import LEGACY_DATABASE_URL into an empty, migrated database. Default is dry-run."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        source = os.environ.get("LEGACY_DATABASE_URL")
        if not source:
            raise CommandError("Set LEGACY_DATABASE_URL in the process environment.")
        if m.User.objects.exists() or m.Post.objects.exists():
            raise CommandError("The target database must be empty. Use a separate migrated database.")
        mapping = [
            (m.Post, "ok_posts"), (m.Growth, "ok_growth"), (m.File, "ok_files"),
            (m.UploadUsage, "ok_upload_usage"), (m.Preference, "ok_preferences"),
            (m.Vote, "ok_votes"), (m.Comment, "ok_comments"), (m.CommentLike, "ok_comment_likes"),
            (m.Message, "ok_messages"), (m.Inbox, "ok_inbox"), (m.Grade, "ok_grades"),
            (m.Notice, "ok_notices"), (m.Follow, "ok_follows"), (m.RemovedPost, "ok_removed_posts"),
        ]
        with psycopg.connect(source, row_factory=dict_row, connect_timeout=15) as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            tables = {row["tablename"] for row in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
            if "ok_accounts" not in tables:
                raise CommandError("The source does not contain the previous ok_accounts table.")
            administrators = {row["actor"] for row in conn.execute("SELECT actor FROM ok_admins")} if "ok_admins" in tables else set()
            with transaction.atomic():
                for row in conn.execute("SELECT * FROM ok_accounts"):
                    password = row["password"]
                    if not re.fullmatch(r"[a-f0-9]{32}:[a-f0-9]{128}", password):
                        raise CommandError("Unexpected password hash format; import rolled back.")
                    salt, digest = password.split(":")
                    m.User.objects.create(
                        code=row["code"], name=row["name"], ring=row["ring"], team=row["team"],
                        password="legacy_scrypt$" + salt + "$" + digest,
                        is_coach=row["role"] == "coach", is_admin=row["code"] in administrators,
                    )
                for model, table in mapping:
                    if table not in tables:
                        continue
                    # Table identifiers come only from the fixed mapping above.
                    order = " ORDER BY parent NULLS FIRST" if table == "ok_comments" else ""
                    for row in conn.execute("SELECT * FROM " + table + order):
                        fields = {}
                        for field in model._meta.local_fields:
                            if not field.column or field.column not in row:
                                continue
                            value = rewrite_urls(row[field.column])
                            if field.get_internal_type() == "BooleanField":
                                value = bool(value)
                            fields[field.attname] = value
                        if model is m.Growth and "publish" not in fields["payload"]:
                            from hashlib import sha256
                            day = str(fields["day"])
                            post_id = "g" + sha256((fields["actor_id"] + ":" + day).encode()).hexdigest()
                            fields["payload"]["publish"] = m.Post.objects.filter(pk=post_id).exists()
                        model.objects.create(**fields)
                self.stdout.write(f"Validated {m.User.objects.count()} accounts and {m.Post.objects.count()} posts.")
                if not options["apply"]:
                    transaction.set_rollback(True)
                    self.stdout.write("Dry run completed. Run with --apply to commit.")
                else:
                    self.stdout.write(self.style.SUCCESS("Import committed. Copy uploaded files separately."))
