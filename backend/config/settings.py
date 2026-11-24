from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")
DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("replace-")):
    raise ValueError("Set a unique SECRET_KEY of at least 50 characters")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"] if DEBUG else [])
if not DEBUG and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ValueError("Set explicit production ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.staticfiles", "rest_framework", "core.apps.CoreConfig",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "core.security.SecurityHeaders",
    "core.health.ReadinessMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": env.db("DATABASE_URL")}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ValueError("DATABASE_URL must identify a PostgreSQL database")
DATABASES["default"].update(CONN_MAX_AGE=60, CONN_HEALTH_CHECKS=True)
DATABASES["default"].setdefault("OPTIONS", {}).update(
    connect_timeout=15, options="-c statement_timeout=10000 -c lock_timeout=3000"
)
CACHES = {"default": {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": env("REDIS_URL"),
    "TIMEOUT": 900,
    "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient",
                "SOCKET_CONNECT_TIMEOUT": 2, "SOCKET_TIMEOUT": 2,
                "SERIALIZER": "django_redis.serializers.json.JSONSerializer"},
    "KEY_PREFIX": "okhovat",
}}
AUTH_USER_MODEL = "core.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "core.hashers.LegacyScryptHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ["code", "name"]}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 604800
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = False
# Internal readiness probes must work over HTTP without redirecting to HTTPS.
# All application pages and other API routes retain HTTPS enforcement.
SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
# Enable only behind a proxy that replaces incoming X-Forwarded-Proto.
if env.bool("TRUST_PROXY_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
TRUSTED_PROXY_COUNT = env.int("TRUSTED_PROXY_COUNT", default=0)
if not 0 <= TRUSTED_PROXY_COUNT <= 3:
    raise ValueError("TRUSTED_PROXY_COUNT must be between 0 and 3")
REST_FRAMEWORK = {
    "NUM_PROXIES": TRUSTED_PROXY_COUNT,
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["core.security.ActiveMember"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser", "rest_framework.parsers.MultiPartParser"],
    "DEFAULT_THROTTLE_CLASSES": ["core.security.MemberThrottle"],
    "DEFAULT_THROTTLE_RATES": {"user": "120/min", "anon": "30/min", "login": "10/min"},
    "EXCEPTION_HANDLER": "core.security.exception_handler",
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 11 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FIELDS = 100
# Keep UPLOADS_DIR as a legacy fallback for files uploaded before purpose-specific
# volumes were introduced. New files are stored in their own persistent volumes.
MEDIA_ROOT = Path(env("UPLOADS_DIR", default=str(BASE_DIR / "private-media")))
AVATARS_DIR = Path(env("AVATARS_DIR", default="/data/avatars"))
POSTS_DIR = Path(env("POSTS_DIR", default="/data/posts"))
SKILLS_DIR = Path(env("SKILLS_DIR", default="/data/skills"))
LANDING_DIR = Path(env("LANDING_DIR", default="/data/landing"))
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_ROOT = BASE_DIR.parent / "frontend" / "dist"
WHITENOISE_ROOT = FRONTEND_ROOT
WHITENOISE_MAX_AGE = 900
LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"okhovat.security": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}
