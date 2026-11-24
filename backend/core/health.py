"""Minimal infrastructure readiness endpoint, with no session or member data."""
import logging
from django.core.cache import cache
from django.db import connection, OperationalError, InterfaceError
from django.http import JsonResponse
from redis.exceptions import RedisError

log = logging.getLogger("okhovat.security")


def readiness(request):
    if request.method not in ("GET", "HEAD"):
        response = JsonResponse({"ok": False}, status=405)
        response["Allow"] = "GET, HEAD"
        return response
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        cache.get("health:probe")
    except (OperationalError, InterfaceError, RedisError, OSError) as error:
        log.warning("readiness_dependency_failed kind=%s", type(error).__name__)
        return JsonResponse({"ok": False}, status=503)
    return JsonResponse({"ok": True})


class ReadinessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Kubernetes probes use the pod IP as Host, not the public site domain.
        # Only this fixed, data-free endpoint bypasses CommonMiddleware host
        # checks and session authentication. All normal routes remain unchanged.
        if request.path_info == "/api/health/":
            return readiness(request)
        return self.get_response(request)
