"""Deployment regressions; service integration still needs a container runtime."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from django.db import OperationalError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from redis.exceptions import ConnectionError as RedisConnectionError


class HealthCheckTests(TestCase):
    @override_settings(SECURE_SSL_REDIRECT=True, ALLOWED_HOSTS=["example.com"])
    def test_http_probe_is_ready_and_does_not_use_login_limit(self):
        client = APIClient()
        for _ in range(35):
            result = client.get("/api/health/", HTTP_HOST="10.0.0.5:8000")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json(), {"ok": True})
        response = client.get("/", HTTP_HOST="example.com")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_cache_failure_reports_unready(self):
        with patch("core.health.cache.get", side_effect=RedisConnectionError("private connection details")):
            result = APIClient().get("/api/health/")
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("private connection details", result.content.decode())

    def test_database_failure_reports_unready(self):
        with patch("core.health.connection.cursor", side_effect=OperationalError("private connection details")):
            result = APIClient().get("/api/health/")
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("private connection details", result.content.decode())


class StartupTests(TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[2] / "deploy" / "prepare.py"
        spec = importlib.util.spec_from_file_location("okhovat_prepare", path)
        self.prepare = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.prepare)

    def test_migration_lock_and_prepare_order(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (True,)
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=Path(folder), AVATARS_DIR=Path(folder), POSTS_DIR=Path(folder), SKILLS_DIR=Path(folder)):
            with patch("django.db.connection.cursor") as factory, patch("django.db.connection.close"), patch("django.core.management.call_command") as command:
                factory.return_value.__enter__.return_value = cursor
                self.prepare.main()
        self.assertEqual([call.args[0] for call in command.call_args_list], ["migrate", "collectstatic", "check"])
        sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn("SELECT pg_try_advisory_lock(%s)", sql)
        self.assertIn("SELECT pg_advisory_unlock(%s)", sql)

    def test_migration_failure_unlocks_and_does_not_continue(self):
        cursor = MagicMock()
        cursor.fetchone.return_value = (True,)
        with TemporaryDirectory() as folder, override_settings(MEDIA_ROOT=Path(folder), AVATARS_DIR=Path(folder), POSTS_DIR=Path(folder), SKILLS_DIR=Path(folder)):
            with patch("django.db.connection.cursor") as factory, patch("django.core.management.call_command", side_effect=RuntimeError("migration failed")) as command:
                factory.return_value.__enter__.return_value = cursor
                with self.assertRaises(RuntimeError):
                    self.prepare.main()
        self.assertEqual(command.call_count, 1)
        cursor.execute.assert_any_call("SELECT pg_advisory_unlock(%s)", [27527001])
