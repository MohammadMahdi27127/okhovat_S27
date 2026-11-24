from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from .models import User, Growth, Post, Vote, Comment, Inbox, Preference, File, UploadUsage
from .hashers import LegacyScryptHasher
from . import attendance


class ConnectedFlows(TestCase):
    def setUp(self):
        cache.clear()
        self.member = User.objects.create_user("27127", "Test-only$Password83", name="عضو", ring="الف", team="آموزش")
        self.peer = User.objects.create_user("27128", "Test-only$Password83", name="هم‌حلقه", ring="الف")
        self.coach = User.objects.create_user("90001", "Test-only$Password83", name="مربی", is_coach=True)
        self.admin = User.objects.create_user("90002", "Test-only$Password83", name="ادمین", is_admin=True)
        self.client = APIClient(enforce_csrf_checks=True)
        self.growth = {"day": timezone.localdate().isoformat(), "dateJalali": "۱۴۰۵/۹/۱", "sport": 1, "reading": 20, "learned": "خصوصی"}

    def signin(self, user=None):
        token = self.client.get("/api/session/").json()["csrf"]
        with patch("core.attendance.lookup", return_value={"status": "unavailable"}):
            response = self.client.post("/api/login/", {"code": (user or self.member).code, "password": "Test-only$Password83"},
                                        format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200, response.content)
        self.client.credentials(HTTP_X_CSRFTOKEN=response.json()["csrf"])

    def test_login_csrf_no_seeding_and_hash(self):
        self.assertEqual(self.client.post("/api/login/", {"code": "27127", "password": "Test-only$Password83"}, format="json").status_code, 403)
        self.signin()
        self.assertTrue(self.member.password.startswith("argon2$"))
        self.assertNotIn("password", self.client.get("/api/session/").json()["user"])
        self.assertEqual(self.client.cookies["sessionid"]["max-age"], 604800)
        self.assertEqual(self.client.get("/api/state/")["Cache-Control"], "no-store, private")

    def test_private_growth_publish_retry_withdraw(self):
        self.signin()
        response = self.client.put("/api/growth/", self.growth, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Growth.objects.count(), 1)
        self.assertEqual(Post.objects.count(), 0)
        published = dict(self.growth, publish=True)
        for _ in range(2):
            response = self.client.put("/api/growth/", published, format="json")
            self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Post.objects.count(), 1)
        self.assertNotIn("خصوصی", str(Post.objects.get().payload))
        pid = Post.objects.get().pk
        Vote.objects.create(post_id=pid, actor=self.peer, kind="like")
        Comment.objects.create(post_id=pid, actor=self.peer, body="نظر")
        self.client.put("/api/growth/", self.growth, format="json")
        self.assertEqual(Post.objects.count(), 0)
        self.assertEqual(Comment.objects.count(), 0)
        self.assertEqual(Growth.objects.count(), 1)

    def test_authorization_and_role_independence(self):
        self.signin()
        self.assertEqual(self.client.get("/api/oversight/").status_code, 403)
        self.assertEqual(self.client.get("/api/admin/reports/").status_code, 403)
        response = self.client.post("/api/admin/members/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.put("/api/growth/", dict(self.growth, is_admin=True), format="json").status_code, 400)
        self.assertEqual(self.client.post("/api/posts/", {"title": "test", "text": "test", "type": "حلقه"}, format="json").status_code, 403)
        self.signin(self.coach)
        self.assertEqual(self.client.get("/api/oversight/").status_code, 200)
        self.assertEqual(self.client.get("/api/admin/reports/").status_code, 403)

    def test_moderation_and_normal_admin_post(self):
        self.signin(self.admin)
        response = self.client.post("/api/posts/", {"title": "پست", "text": "متن"}, format="json")
        self.assertEqual(response.status_code, 201, response.content)
        pid = response.json()["id"]
        self.assertFalse(self.client.get("/api/posts/").json()["results"][0]["coachPost"])
        self.client.delete("/api/posts/" + pid + "/")
        self.assertEqual(self.client.get("/api/posts/").json()["results"], [])
        self.assertEqual(self.client.put("/api/posts/" + pid + "/votes/like/", {"active": True}, format="json").status_code, 404)

    def test_message_target_and_archive(self):
        self.signin(self.coach)
        response = self.client.post("/api/messages/", {"scope": "person", "target": self.member.code, "text": "سلام"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Inbox.objects.count(), 1)
        self.assertEqual(len(self.client.get("/api/state/").json()["archive"]), 1)
        self.signin(self.peer)
        self.assertEqual(self.client.get("/api/state/").json()["messages"], [])
        self.signin()
        self.assertEqual(len(self.client.get("/api/state/").json()["messages"]), 1)

    def test_growth_object_scope_and_cache_invalidation(self):
        self.signin()
        self.client.put("/api/growth/", self.growth, format="json")
        self.assertEqual(len(self.client.get("/api/state/").json()["growth"]), 1)
        self.signin(self.peer)
        self.assertEqual(self.client.get("/api/state/").json()["growth"], [])
        self.signin(self.coach)
        self.assertEqual(len(self.client.get("/api/oversight/?person=" + self.member.code).json()["reports"]), 1)

    def test_password_change_and_login_throttle(self):
        self.signin()
        response = self.client.post("/api/password/", {"current": "Test-only$Password83", "password": "New-long$Secret987"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        self.member.refresh_from_db()
        self.assertTrue(self.member.check_password("New-long$Secret987"))
        self.assertEqual(self.client.get("/api/session/").json()["user"]["code"], self.member.code)
        self.client.post("/api/logout/")
        token = self.client.get("/api/session/").json()["csrf"]
        for _ in range(10):
            response = self.client.post("/api/login/", {"code": "wrong", "password": "wrong"}, format="json", HTTP_X_CSRFTOKEN=token)
        # Invalid input is rejected before authentication.
        self.assertEqual(response.status_code, 400)
        for _ in range(11):
            response = self.client.post("/api/login/", {"code": "12345", "password": "wrong"}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 429)

    def test_legacy_hash(self):
        import hashlib
        salt = "a" * 32
        digest = hashlib.scrypt(b"old-password", salt=salt.encode(), n=16384, r=8, p=1).hex()
        self.member.password = "legacy_scrypt$" + salt + "$" + digest
        self.member.save()
        self.assertTrue(self.member.check_password("old-password"))
        self.member.refresh_from_db()
        self.assertTrue(self.member.password.startswith("argon2$"))

    def test_sheet_layout(self):
        rows = [["کد گروهی", "تعداد حاضرین"], ["1", "حلقه الف"], ["27127", "نام", "89", "86.41%"], ["27128", "همراه", "0", "0%"], ["2", "حلقه ب"], ["27129", "دیگر", "2", "20%"]]
        result = attendance.extract(rows, "27127")
        self.assertEqual(result["percent"], 86.41)
        self.assertEqual(result["peers"], [{"name": "همراه", "percent": 0}])


    def test_upload_privacy_and_malformed_input(self):
        from django.test import override_settings
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from django.core.files.uploadedfile import SimpleUploadedFile
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=Path(folder), AVATARS_DIR=Path(folder), POSTS_DIR=Path(folder), SKILLS_DIR=Path(folder)):
            self.signin()
            upload = self.client.post("/api/files/upload/proof/",
                                      {"file": SimpleUploadedFile("proof.txt", b"private file")}, format="multipart")
            self.assertEqual(upload.status_code, 200, upload.content)
            url = upload.json()["url"]
            self.assertEqual(self.client.get(url).status_code, 200)
            stored = File.objects.get(pk=url.split("/")[-2])
            self.assertEqual(stored.size_bytes, len(b"private file"))
            self.assertGreaterEqual(stored.quota_bytes, stored.size_bytes)
            self.signin(self.peer)
            self.assertEqual(self.client.get(url).status_code, 403)
            self.signin(self.coach)
            self.assertEqual(self.client.get(url).status_code, 200)
            self.assertEqual(self.client.put("/api/profile/avatar/", [], format="json").status_code, 400)
            self.assertEqual(self.client.put("/api/growth/", [{"bad": "data"}], format="json").status_code, 400)


    def test_weekly_post_cleanup_removes_media_and_releases_quota_but_keeps_post(self):
        from django.test import override_settings
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from django.utils import timezone
        from datetime import timedelta
        from core.storage import storage_dir
        with TemporaryDirectory() as folder, override_settings(
            MEDIA_ROOT=Path(folder), AVATARS_DIR=Path(folder) / "avatars",
            POSTS_DIR=Path(folder) / "posts", SKILLS_DIR=Path(folder) / "skills",
        ):
            owner = self.member
            post_file = File.objects.create(
                owner=owner, purpose="post", name="old.jpg", mime="image/jpeg",
                uploaded_at=timezone.now() - timedelta(days=8), size_bytes=5000, quota_bytes=5000,
            )
            target = storage_dir("post") / post_file.id
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"x" * 5000)
            UploadUsage.objects.create(actor=owner, used=5000)
            post = Post.objects.create(actor=owner, payload={"text": "متن باقی بماند", "image": f"/api/files/{post_file.id}/"})
            call_command("cleanup_post_files", days=7, verbosity=0)
            self.assertFalse(File.objects.filter(pk=post_file.pk).exists())
            self.assertFalse(target.exists())
            self.assertEqual(UploadUsage.objects.get(actor=owner).used, 0)
            post.refresh_from_db()
            self.assertEqual(post.payload["text"], "متن باقی بماند")

    def test_last_admin_and_immediate_role_change(self):
        self.signin(self.admin)
        body = {"is_admin": False, "is_coach": False, "is_ring_leader": False,
                "is_workgroup_manager": False, "ring": "", "team": ""}
        response = self.client.put("/api/admin/members/" + self.admin.code + "/roles/", body, format="json")
        self.assertEqual(response.status_code, 400)
        self.client.put("/api/admin/members/" + self.member.code + "/roles/",
                        dict(body, is_coach=True), format="json")
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_coach)
        self.signin()
        self.assertEqual(self.client.get("/api/oversight/").status_code, 200)

    def test_suspended_session_and_finite_numbers(self):
        self.signin()
        response = self.client.put("/api/growth/", dict(self.growth, sport="NaN"), format="json")
        self.assertEqual(response.status_code, 400)
        self.member.suspended_until = timezone.now() + timedelta(days=1)
        self.member.save()
        self.assertEqual(self.client.get("/api/state/").status_code, 403)

    def test_cache_backend_failure_is_controlled(self):
        from redis.exceptions import ConnectionError
        self.signin()
        with patch("core.security.cache.get", side_effect=ConnectionError()):
            self.assertEqual(self.client.get("/api/state/").status_code, 503)

    def test_no_seeded_accounts_from_migrations(self):
        # No data migrations, startup hooks, or management defaults create accounts.
        from django.db.migrations.loader import MigrationLoader
        from django.db import connection
        from django.db.migrations.operations.special import RunPython
        loader = MigrationLoader(connection)
        for key, migration in loader.disk_migrations.items():
            if key[0] == "core":
                self.assertFalse(any(isinstance(op, RunPython) for op in migration.operations))

    def test_feed_counts_and_shared_post_filter(self):
        self.signin()
        post = Post.objects.create(actor=self.member, payload={"title": "عنوان", "text": "متن", "type": "شخصی"})
        Post.objects.create(actor=self.peer, payload={"title": "دیگر", "text": "متن", "type": "شخصی"})
        Vote.objects.create(post=post, actor=self.peer, kind="like")
        Vote.objects.create(post=post, actor=self.peer, kind="recommend")
        Comment.objects.create(post=post, actor=self.peer, body="اول")
        Comment.objects.create(post=post, actor=self.peer, body="دوم")
        rows = self.client.get("/api/posts/?id=" + post.id).json()["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["likes"], rows[0]["comments"]), (1, 2))
        self.assertTrue(rows[0]["trending"])
        comments = self.client.get("/api/posts/" + post.id + "/comments/").json()
        self.assertEqual(len(comments), 2)

    def test_rankings_weights_and_external_likes(self):
        from .models import Grade
        self.signin()
        Grade.objects.create(kind="ring", target="الف", score=10, coach=self.coach)
        Preference.objects.update_or_create(actor=self.member, name="attendance", defaults={"value": {"status": "ok", "percent": 60}})
        Preference.objects.create(actor=self.peer, name="attendance", value={"status": "ok", "percent": 80})
        Growth.objects.create(actor=self.member, day=timezone.localdate(), sport=1, reading=20)
        post = Post.objects.create(actor=self.member, payload={"type": "حلقه", "ring": "الف"})
        Vote.objects.create(post=post, actor=self.peer, kind="like")
        Vote.objects.create(post=post, actor=self.admin, kind="like")
        rows = self.client.get("/api/rankings/").json()
        self.assertEqual(rows[0]["attendance"], 70)
        self.assertEqual(rows[0]["total"], 183)

    def test_assistant_limits_data_to_own_ring(self):
        Growth.objects.create(actor=self.member, day=timezone.localdate(), sport=1, reading=20)
        Growth.objects.create(actor=self.peer, day=timezone.localdate(), sport=2, reading=30)
        Growth.objects.create(actor=self.admin, day=timezone.localdate(), sport=9, reading=900)
        self.signin()
        with patch("core.views.interpret", side_effect=lambda text, fallback: fallback):
            own = self.client.post("/api/assistant/chat/", {"message": "آمار رشد امروز"}, format="json").json()["text"]
            ring = self.client.post("/api/assistant/chat/", {"message": "آمار رشد حلقه امروز"}, format="json").json()["text"]
        self.assertIn("1 ساعت ورزش", own)
        self.assertIn("3 ساعت ورزش", ring)
        self.assertIn("50 صفحه", ring)
        self.assertNotIn("900", ring)
