"""Opt-in tests against dedicated PostgreSQL and Redis services, never production."""
import os
from .settings import *
if not os.environ.get("TEST_REDIS_URL"):
    raise ValueError("TEST_REDIS_URL must point to a disposable, dedicated Redis database")
CACHES["default"]["LOCATION"] = os.environ["TEST_REDIS_URL"]
CACHES["default"]["KEY_PREFIX"] = "okhovat-tests"
DATABASES["default"]["TEST"] = {"NAME": "test_okhovat"}
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
