from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.urls import include, path, re_path

def frontend(request):
    index = settings.FRONTEND_ROOT / "index.html"
    if not index.exists():
        return HttpResponse("Build frontend with npm ci && npm run build.", status=503)
    response = FileResponse(index.open("rb"), content_type="text/html")
    response["Cache-Control"] = "no-cache"
    return response

urlpatterns = [
    path("api/", include("core.urls")),
    re_path(r"^(?!api/).*", frontend),
]
