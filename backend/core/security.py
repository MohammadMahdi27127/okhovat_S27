import hashlib
import logging
import uuid
from django.conf import settings
from django.core.cache import cache
from django.db import OperationalError, InterfaceError
from django.http import JsonResponse
from django.middleware.csrf import CsrfViewMiddleware
from rest_framework.exceptions import APIException, PermissionDenied, Throttled
from rest_framework.permissions import BasePermission
from rest_framework.throttling import UserRateThrottle
from redis.exceptions import RedisError

log = logging.getLogger("okhovat.security")


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "سرویس موقتاً در دسترس نیست. کمی بعد تلاش کنید."


class ActiveMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and not request.user.suspended)


class CoachOnly(ActiveMember):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_coach


class AdminOnly(ActiveMember):
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_admin


class MemberThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        self.scope = "user" if request.user.is_authenticated else "anon"
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        try:
            return super().allow_request(request, view)
        except (RedisError, OSError):
            raise ServiceUnavailable()


def check_login_rate(request, code):
    # Two independent limits; keys never contain a raw code or password.
    for category, value in [("address", UserRateThrottle().get_ident(request)), ("account", code)]:
        key = "login:" + category + ":" + hashlib.sha256(value.encode()).hexdigest()
        try:
            if cache.add(key, 1, timeout=60):
                count = 1
            else:
                count = cache.incr(key)
        except ValueError:
            count = 1
            cache.add(key, 1, timeout=60)
        except (RedisError, OSError):
            raise ServiceUnavailable()
        if count > 10:
            log.warning("login_throttled category=%s", category)
            raise Throttled(wait=60)


def require_csrf(request):
    checker = CsrfViewMiddleware(lambda req: None)
    checker.process_request(request)
    if checker.process_view(request, lambda req: None, (), {}):
        raise PermissionDenied("اعتبار درخواست منقضی شده است. صفحه را تازه کنید.")


def exception_handler(exc, context):
    from rest_framework.views import exception_handler as drf_handler
    if isinstance(exc, (OperationalError, InterfaceError, RedisError, OSError)):
        log.error("dependency_failed kind=%s", type(exc).__name__)
        exc = ServiceUnavailable()
    return drf_handler(exc, context)


class SecurityHeaders:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = uuid.uuid4().hex
        if request.path.startswith("/api/"):
            try:
                length = int(request.META.get("CONTENT_LENGTH") or 0)
            except ValueError:
                return JsonResponse({"detail": "درخواست معتبر نیست."}, status=400)
            if length > settings.DATA_UPLOAD_MAX_MEMORY_SIZE:
                return JsonResponse({"detail": "حداکثر حجم فایل ۱۰ مگابایت است."}, status=413)
        response = self.get_response(request)
        response["X-Request-ID"] = request_id
        response["X-Frame-Options"] = "DENY"
        response["X-Content-Type-Options"] = "nosniff"
        response["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' blob: data:; "
            "media-src 'self' blob:; connect-src 'self'; object-src 'none'; base-uri 'self'; "
            "frame-ancestors 'none'; form-action 'self'"
        )
        if request.path.startswith("/api/files/") and response.status_code == 200:
            # کارت‌های HTML لندینگ باید در iframe همان دامنه قابل نمایش باشند.
            response["X-Frame-Options"] = "SAMEORIGIN"
            response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store, private"
            response["Vary"] = "Cookie"
            if response.status_code >= 400:
                log.warning("api_failure method=%s status=%s request_id=%s",
                            request.method, response.status_code, request_id)
        return response
