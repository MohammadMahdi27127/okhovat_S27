"""Check the web service and its dependencies without exposing credentials."""
import json
import sys
from urllib.request import ProxyHandler, build_opener

try:
    # Ignore outbound HTTP_PROXY settings for this loopback-only probe.
    with build_opener(ProxyHandler({})).open("http://127.0.0.1:8000/api/health/", timeout=18) as response:
        healthy = response.status == 200 and json.loads(response.read(1024)).get("ok") is True
    sys.exit(0 if healthy else 1)
except Exception:
    sys.exit(1)
