import io
import json
import re
import logging
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from PIL import Image, UnidentifiedImageError
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction, connection
from django.db.models import Count, Sum, Q, Exists, OuterRef, Subquery
from django.http import FileResponse
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from redis.exceptions import RedisError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from . import models as m, serializers as s, attendance
from .storage import storage_dir, file_path, delete_file_and_release_quota
from .security import CoachOnly, AdminOnly, require_csrf, check_login_rate
from .assistant import periods, interpret
from .health import readiness as health

log = logging.getLogger("okhovat.security")


def validated(serializer, request):
    form = serializer(data=request.data)
    form.is_valid(raise_exception=True)
    return form.validated_data


def json_data(value):
    return json.loads(json.dumps(value, cls=DjangoJSONEncoder))


def visible_posts():
    return m.Post.objects.filter(removedpost__isnull=True)


def announce(author, kind="post", recipient=None):
    recipients = m.User.objects.filter(is_active=True).exclude(pk=author.pk)
    if recipient is not None:
        recipients = recipients.filter(pk=recipient)
    m.Notice.objects.bulk_create(
        [m.Notice(recipient=user, kind=kind) for user in recipients.iterator()], batch_size=500
    )


def audit(user, action, target=""):
    m.AuditEvent.objects.create(actor=user, action=action, target=str(target)[:100])
    log.info("audit action=%s actor=%s", action, user.pk)


@api_view(["GET"])
@permission_classes([AllowAny])
def session(request):
    user = request.user
    active = user.is_authenticated and user.is_active and not user.suspended
    return Response({
        "user": s.UserOutput(user).data if active else None,
        "attendance": request.session.get("attendance") if active else None,
        "csrf": get_token(request),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def sign_in(request):
    require_csrf(request._request)
    data = validated(s.LoginInput, request)
    check_login_rate(request, data["code"])
    user = authenticate(request, username=data["code"], password=data["password"])
    if not user or user.suspended:
        log.warning("login_failed")
        return Response({"detail": "کد گروهی یا رمز عبور درست نیست."}, status=401)
    login(request, user)
    request.session.set_expiry(604800)
    request.session["attendance"] = attendance.lookup(user.code) if not user.is_coach else None
    if request.session["attendance"] is not None:
        m.Preference.objects.update_or_create(
            actor=user, name="attendance", defaults={"value": request.session["attendance"]}
        )
    audit(user, "login")
    return Response({"user": s.UserOutput(user).data, "csrf": get_token(request)})


@api_view(["POST"])
def sign_out(request):
    logout(request)
    return Response({"ok": True})


@api_view(["POST"])
def change_password(request):
    data = validated(s.PasswordInput, request)
    if not request.user.check_password(data["current"]):
        raise ValidationError("رمز فعلی درست نیست.")
    try:
        validate_password(data["password"], request.user)
    except DjangoValidationError as error:
        raise ValidationError(error.messages)
    request.user.set_password(data["password"])
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)
    audit(request.user, "password_changed")
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([AdminOnly])
def register(request):
    data = validated(s.RegisterInput, request)
    if m.User.objects.filter(pk=data["code"]).exists():
        return Response({"detail": "این کد قبلاً ثبت شده است."}, status=409)
    with transaction.atomic():
        user = m.User.objects.create_user(**data)
        audit(request.user, "member_created", user.code)
    return Response(s.UserOutput(user).data, status=201)


@api_view(["POST"])
@permission_classes([AdminOnly])
def suspend(request, code):
    days = validated(s.SuspendInput, request)["days"]
    if days not in (1, 3):
        raise ValidationError("مدت تعلیق باید یک یا سه روز باشد.")
    user = get_object_or_404(m.User, pk=code)
    if user.is_admin:
        raise PermissionDenied("تعلیق ادمین از این مسیر مجاز نیست.")
    user.suspended_until = timezone.now() + timedelta(days=days)
    user.save(update_fields=["suspended_until"])
    audit(request.user, "suspended", code)
    return Response({"ok": True})


def owned_file(user, path, purpose):
    if not path:
        return None
    match = re.fullmatch(r"/api/files/([a-f0-9]{32})/", path)
    if not match:
        raise ValidationError("نشانی فایل معتبر نیست.")
    file = get_object_or_404(m.File, pk=match[1], owner=user, purpose=purpose)
    if m.RemovedPost.objects.filter(media=path).exists():
        raise ValidationError("فایل حذف‌شده قابل انتشار نیست.")
    return file


@api_view(["PUT"])
def growth(request):
    data = validated(s.GrowthInput, request)
    owned_file(request.user, data["proof"], "proof")
    payload = json_data(data)
    post_id = "g" + sha256((request.user.code + ":" + data["day"].isoformat()).encode()).hexdigest()
    with transaction.atomic():
        # Serialize saves for this actor so concurrent retries cannot disagree on publication.
        m.User.objects.select_for_update().get(pk=request.user.pk)
        m.Growth.objects.update_or_create(
            actor=request.user, day=data["day"],
            defaults={"sport": data["sport"], "reading": data["reading"], "payload": payload},
        )
        if data["publish"]:
            public = {
                "type": "رشد فردی", "title": "گزارش رشد · " + data["dateJalali"],
                "text": f'{data["sport"]:g} ساعت ورزش و {data["reading"]} صفحه مطالعه' +
                        (" · " + data["skillTitle"] if data["skillTitle"] else ""),
                "growthDay": data["day"].isoformat(),
            }
            post, created = m.Post.objects.update_or_create(
                pk=post_id, defaults={"actor": request.user, "payload": public}
            )
            if created:
                announce(request.user)
        elif not m.RemovedPost.objects.filter(post_id=post_id).exists():
            m.Post.objects.filter(pk=post_id, actor=request.user).delete()
    return Response({"id": post_id if data["publish"] else None})


def post_queryset(user):
    return visible_posts().select_related("actor").annotate(
        like_count=Count("vote__actor_id", filter=Q(vote__kind="like"), distinct=True),
        comment_count=Count("comment", distinct=True),
        viewer_liked=Exists(m.Vote.objects.filter(post_id=OuterRef("pk"), actor=user, kind="like")),
        viewer_recommended=Exists(m.Vote.objects.filter(post_id=OuterRef("pk"), actor=user, kind="recommend")),
        viewer_bookmarked=Exists(m.Vote.objects.filter(post_id=OuterRef("pk"), actor=user, kind="bookmark")),
        is_trending=Exists(m.Vote.objects.filter(post_id=OuterRef("pk"), kind="recommend")),
        author_avatar=Subquery(m.Preference.objects.filter(actor_id=OuterRef("actor_id"), name="avatar").values("value")[:1]),
    )


def post_output(post, user):
    payload = dict(post.payload)
    media_url = next((payload.get(k) for k in ("image", "video", "file") if payload.get(k)), None)
    if media_url and re.fullmatch(r"/api/files/[a-f0-9]{32}/", media_url):
        media_id = media_url.rsplit("/", 2)[-2]
        if not m.File.objects.filter(pk=media_id).exists():
            payload.pop("image", None)
            payload.pop("video", None)
            payload.pop("file", None)
            payload["mediaExpired"] = True
    payload.update(
        id=post.id, authorId=post.actor_id, name=post.actor.name,
        coachPost=post.actor.is_coach, ring=payload.get("ring", post.actor.ring),
        group=payload.get("group", post.actor.team), createdAt=post.created.isoformat(),
        likes=post.like_count, liked=post.viewer_liked, recommended=post.viewer_recommended,
        trending=post.is_trending, bookmarked=post.viewer_bookmarked,
        comments=post.comment_count, avatar=post.author_avatar or "",
    )
    return payload


@api_view(["GET", "POST"])
def posts(request):
    if request.method == "GET":
        try:
            page = max(1, min(10000, int(request.query_params.get("page", "1"))))
        except ValueError:
            raise ValidationError("شماره صفحه معتبر نیست.")
        rows = post_queryset(request.user)
        if post_id := request.query_params.get("id"):
            rows = rows.filter(pk=post_id)
        tab = request.query_params.get("tab")
        if tab == "following":
            rows = rows.filter(actor_id__in=m.Follow.objects.filter(actor=request.user).values("target_id"))
        if tab == "trending":
            rows = rows.filter(is_trending=True)
        kind = request.query_params.get("type", "همه")
        if kind != "همه":
            rows = rows.filter(payload__type=kind)
        batch = list(rows[(page - 1) * 30:page * 30 + 1])
        return Response({"results": [post_output(p, request.user) for p in batch[:30]], "more": len(batch) > 30})
    data = validated(s.PostInput, request)
    if data["type"] == "حلقه" and not (request.user.is_ring_leader and request.user.ring):
        raise PermissionDenied("ثبت برنامه برای مسئول حلقه فعال است.")
    if data["type"] == "کارگروه" and not (request.user.is_workgroup_manager and request.user.team):
        raise PermissionDenied("ثبت جلسه برای مسئول کارگروه فعال است.")
    allowed_people = m.User.objects.filter(is_active=True)
    if data["type"] == "حلقه":
        allowed_people = allowed_people.filter(ring=request.user.ring)
    elif data["type"] == "کارگروه":
        allowed_people = allowed_people.filter(team=request.user.team)
    elif data["people"]:
        raise ValidationError("فهرست همراهان فقط برای برنامه و جلسه است.")
    if set(data["people"]) - set(allowed_people.values_list("code", flat=True)):
        raise ValidationError("یکی از همراهان عضو گروه مربوطه نیست.")
    file = owned_file(request.user, data.pop("attachment"), "post")
    data = json_data(data)
    if file:
        key = "image" if file.mime.startswith("image/") else "video" if file.mime.startswith("video/") else "file"
        data[key] = f"/api/files/{file.id}/"
    if data["type"] == "حلقه":
        data["ring"] = request.user.ring
    if data["type"] == "کارگروه":
        data["group"] = request.user.team
    with transaction.atomic():
        post = m.Post.objects.create(actor=request.user, payload=data)
        announce(request.user)
    return Response({"id": post.id}, status=201)


@api_view(["DELETE"])
@permission_classes([AdminOnly])
def delete_post(request, pid):
    post = get_object_or_404(m.Post, pk=pid)
    media = next((post.payload.get(k) for k in ("image", "video", "file") if post.payload.get(k)), "")
    file_id = None
    match = re.fullmatch(r"/api/files/([a-f0-9]{32})/?", media or "")
    if match:
        file_id = match.group(1)
    with transaction.atomic():
        m.RemovedPost.objects.get_or_create(post=post, defaults={"moderator": request.user, "media": media})
        audit(request.user, "post_removed", pid)
    if file_id:
        # A single uploaded attachment may have been reused by another post.
        still_referenced = visible_posts().exclude(pk=pid).filter(
            Q(payload__image=media) | Q(payload__video=media) | Q(payload__file=media)
        ).exists()
        if not still_referenced:
            delete_file_and_release_quota(file_id)
    return Response({"ok": True})


@api_view(["PUT"])
def vote(request, pid, kind):
    if kind not in ("like", "recommend", "bookmark"):
        raise ValidationError("واکنش معتبر نیست.")
    active = validated(s.ToggleInput, request)["active"]
    with transaction.atomic():
        # Lock only ok_posts: visible_posts() LEFT JOINs ok_removed_posts, and Postgres rejects plain FOR UPDATE on the nullable side of an outer join (0A000).
        post = get_object_or_404(visible_posts().select_for_update(of=("self",)), pk=pid)
        params = {"post": post, "actor": request.user, "kind": kind}
        if active:
            _, created = m.Vote.objects.get_or_create(**params)
            if created and kind == "like":
                announce(request.user, "like", post.actor_id)
        else:
            m.Vote.objects.filter(**params).delete()
    return Response({"ok": True})


@api_view(["GET", "POST"])
def comments(request, pid):
    post = get_object_or_404(visible_posts(), pk=pid)
    if request.method == "GET":
        rows = post.comment_set.select_related("actor").annotate(
            like_count=Count("commentlike__actor_id"),
            viewer_liked=Exists(m.CommentLike.objects.filter(comment_id=OuterRef("pk"), actor=request.user)),
        ).order_by("-created")[:300]
        return Response([{
            "id": c.id, "name": c.actor.name, "text": c.body, "parent": c.parent_id,
            "likes": c.like_count, "liked": c.viewer_liked
        } for c in reversed(list(rows))])
    data = validated(s.CommentInput, request)
    parent = None
    if data.get("parent"):
        parent = get_object_or_404(m.Comment, pk=data["parent"], post=post, parent__isnull=True)
    with transaction.atomic():
        # Lock only ok_posts: visible_posts() LEFT JOINs ok_removed_posts, and Postgres rejects plain FOR UPDATE on the nullable side of an outer join (0A000).
        post = get_object_or_404(visible_posts().select_for_update(of=("self",)), pk=pid)
        item = m.Comment.objects.create(post=post, actor=request.user, parent=parent, body=data["text"])
        announce(request.user, "comment", post.actor_id)
    return Response({"id": item.pk}, status=201)


@api_view(["PUT"])
def comment_like(request, cid):
    active = validated(s.ToggleInput, request)["active"]
    item = get_object_or_404(m.Comment, pk=cid, post__removedpost__isnull=True)
    if active:
        m.CommentLike.objects.get_or_create(comment=item, actor=request.user)
    else:
        m.CommentLike.objects.filter(comment=item, actor=request.user).delete()
    return Response({"ok": True})


@api_view(["PUT"])
def follow(request, code):
    active = validated(s.ToggleInput, request)["active"]
    target = get_object_or_404(m.User, pk=code, is_active=True)
    if target == request.user:
        raise ValidationError("دنبال‌کردن خودتان مجاز نیست.")
    if active:
        m.Follow.objects.get_or_create(actor=request.user, target=target)
    else:
        m.Follow.objects.filter(actor=request.user, target=target).delete()
    return Response({"ok": True})


@api_view(["PUT"])
def profile_status(request):
    data = validated(s.StatusInput, request)
    m.Preference.objects.update_or_create(actor=request.user, name="personalStatus", defaults={"value": data})
    return Response({"ok": True})


@api_view(["PUT"])
def avatar(request):
    path = validated(s.AvatarInput, request)["url"]
    owned_file(request.user, path, "avatar")
    m.Preference.objects.update_or_create(actor=request.user, name="avatar", defaults={"value": path})
    return Response({"ok": True})


@api_view(["POST"])
def upload(request, purpose):
    if purpose not in ("avatar", "proof", "post", "landing"):
        raise ValidationError("کاربرد فایل معتبر نیست.")
    max_size = 1 * 1024 * 1024 if purpose == "landing" else 10 * 1024 * 1024
    size_label = "۱ مگابایت" if purpose == "landing" else "۱۰ مگابایت"
    incoming = request.FILES.get("file")
    filename = Path(incoming.name).name if incoming else ""
    is_html = bool(incoming) and (
        incoming.content_type == "text/html" or Path(filename).suffix.lower() in (".html", ".htm")
    )
    if not incoming or incoming.size > max_size:
        raise ValidationError(f"یک فایل با حداکثر حجم {size_label} انتخاب کنید.")
    data = incoming.read(max_size + 1)
    if len(data) > max_size:
        raise ValidationError("حجم فایل بیش از حد مجاز است.")
    mime = "application/octet-stream"
    if purpose == "landing" and is_html:
        # کارت لندینگ می‌تواند HTML خام باشد؛ آن را به تصویر تبدیل نکن.
        mime = "text/html; charset=utf-8"
    else:
        # Decode and re-encode images, stripping metadata and active/polyglot payloads.
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.width * image.height > 20000000:
                    raise ValidationError("ابعاد تصویر بیش از حد مجاز است.")
                image.load()
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, "JPEG", quality=90)
                data, mime = buffer.getvalue(), "image/jpeg"
        except (UnidentifiedImageError, OSError):
            if purpose == "avatar":
                raise ValidationError("تصویر معتبر انتخاب کنید.")
            if data[4:8] == b"ftyp":
                mime = "video/mp4"
        except Image.DecompressionBombError:
            raise ValidationError("ابعاد تصویر بیش از حد مجاز است.")
    if len(data) > max_size:
        raise ValidationError("تصویر پردازش‌شده بیش از حد مجاز است.")
    folder = storage_dir(purpose)
    folder.mkdir(parents=True, exist_ok=True)
    item = m.File(owner=request.user, purpose=purpose, name=Path(incoming.name).name[:255], mime=mime)
    path = folder / item.id
    charge = max(len(data), 4096)
    item.size_bytes = len(data)
    item.quota_bytes = charge
    try:
        with transaction.atomic():
            m.User.objects.select_for_update().get(pk=request.user.pk)
            usage, _ = m.UploadUsage.objects.get_or_create(actor=request.user)
            if usage.used + charge > 256 * 1024 * 1024:
                raise ValidationError("سهمیهٔ فایل این حساب تکمیل شده است.")
            path.write_bytes(data)
            item.save()
            usage.used += charge
            usage.save(update_fields=["used"])
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return Response({"url": f"/api/files/{item.id}/", "medium": mime.split("/")[0] if mime != "application/octet-stream" else "file"})


@api_view(["GET"])
@permission_classes([AllowAny])
def download(request, fid):
    item = get_object_or_404(m.File, pk=fid)
    if item.purpose == "landing":
        pass  # عمومی — قبل و بعد از ورود قابل مشاهده
    elif not (request.user.is_authenticated and request.user.is_active and not request.user.suspended):
        raise PermissionDenied()
    elif item.purpose == "proof" and item.owner_id != request.user.pk and not request.user.is_coach:
        raise PermissionDenied()
    elif item.purpose == "post":
        path_url = f"/api/files/{fid}/"
        if m.RemovedPost.objects.filter(media__in=[path_url, path_url.rstrip("/")]).exists():
            raise PermissionDenied()
        referenced = visible_posts().filter(
            Q(payload__image=path_url) | Q(payload__video=path_url) | Q(payload__file=path_url)
        ).exists()
        if item.owner_id != request.user.pk and not referenced:
            raise PermissionDenied()
    path = file_path(item)
    if not path.is_file():
        from django.http import Http404
        raise Http404
    response = FileResponse(path.open("rb"), content_type=item.mime,
                            as_attachment=item.mime == "application/octet-stream", filename=item.name)
    return response


@api_view(["POST"])
@permission_classes([CoachOnly])
def send_message(request):
    data = validated(s.MessageInput, request)
    members = m.User.objects.filter(is_active=True, is_coach=False)
    column = {"person": "code", "ring": "ring", "group": "team"}.get(data["scope"])
    if column:
        if not data["target"]:
            raise ValidationError("مخاطب را انتخاب کنید.")
        members = members.filter(**{column: data["target"]})
    if not members.exists():
        raise ValidationError("مخاطبی پیدا نشد.")
    with transaction.atomic():
        item = m.Message.objects.create(sender=request.user, label=data["target"] or "همهٔ اعضا", body=data["text"])
        m.Inbox.objects.bulk_create([m.Inbox(message=item, actor=user) for user in members])
    return Response({"id": item.id})


@api_view(["POST"])
def read_messages(request):
    m.Inbox.objects.filter(actor=request.user).update(seen=True)
    m.Revision.objects.update_or_create(pk=1, defaults={"rev": m.identifier()})
    return Response({"ok": True})


@api_view(["PUT"])
@permission_classes([CoachOnly])
def grade(request, kind):
    if kind not in ("ring", "group"):
        raise ValidationError("نوع امتیاز معتبر نیست.")
    data = validated(s.GradeInput, request)
    column = "ring" if kind == "ring" else "team"
    if not m.User.objects.filter(**{column: data["target"]}).exists():
        raise ValidationError("گروه پیدا نشد.")
    m.Grade.objects.update_or_create(kind=kind, target=data["target"],
                                    defaults={"score": data["score"], "coach": request.user})
    return Response({"ok": True})


@api_view(["POST"])
def notices_read(request):
    m.Notice.objects.filter(recipient=request.user).update(seen=True)
    m.Revision.objects.update_or_create(pk=1, defaults={"rev": m.identifier()})
    return Response({"ok": True})


def build_state(user):
    growth_rows = m.Growth.objects.select_related("actor").filter(actor=user)
    growth_rows = growth_rows.filter(day__gte=timezone.localdate() - timedelta(days=366))
    prefs = {p.name: p.value for p in m.Preference.objects.filter(actor=user)}
    people = m.User.objects.filter(is_active=True)
    directory = s.UserOutput(people[:2000], many=True).data if user.is_coach or user.is_admin else []
    if user.is_admin:
        bale_ids = dict(people.values_list("code", "bale_id"))
        directory = [dict(person, bale_id=bale_ids[person["code"]]) for person in directory]
    inbox = m.Inbox.objects.filter(actor=user).select_related("message", "message__sender")[:200]
    received = [{"id": i.message_id, "text": i.message.body, "name": i.message.sender.name,
                 "date": i.message.created.isoformat(), "seen": i.seen} for i in inbox]
    archive = list(m.Message.objects.filter(sender=user).values("id", "label", "body", "created")[:200])
    notifications = list(m.Notice.objects.filter(recipient=user, seen=False).values("kind").annotate(count=Count("id")))
    return json_data({
        "growth": [dict(g.payload, userId=g.actor_id, userName=g.actor.name, ring=g.actor.ring,
                        group=g.actor.team, day=g.day.isoformat()) for g in growth_rows[:367]],
        "stats": {"posts": visible_posts().filter(actor=user).count(),
                  "growth": m.Growth.objects.filter(actor=user).count(),
                  "followers": m.Follow.objects.filter(target=user).count(),
                  "following": m.Follow.objects.filter(actor=user).count()},
        "programPeople": list(people.filter(Q(ring=user.ring) if user.is_ring_leader and user.ring else Q(pk__in=[])).values("code", "name", "ring", "team"))
            + list(people.filter(Q(team=user.team) if user.is_workgroup_manager and user.team else Q(pk__in=[])).values("code", "name", "ring", "team")),
        "following": list(m.Follow.objects.filter(actor=user).values_list("target_id", flat=True)),
        "preferences": prefs, "directory": directory, "messages": received, "archive": archive,
        "notifications": notifications,
        "ringGrades": dict(m.Grade.objects.filter(kind="ring").values_list("target", "score")),
        "groupGrades": dict(m.Grade.objects.filter(kind="group").values_list("target", "score")),
        "landing": list(m.LandingContent.objects.values("id", "team", "title", "body")[:100]),
        "forms": list(m.CustomForm.objects.values("id", "title", "team", "questions")[:100]),
        "answers": list(m.FormResponse.objects.filter(actor=user).values("form_id", "answers")),
    })


@api_view(["GET"])
def state(request):
    revision = m.Revision.objects.filter(pk=1).values_list("rev", flat=True).first() or "0"
    user = request.user
    key = f"state:{user.pk}:{int(user.is_coach)}:{int(user.is_admin)}:{revision}"
    try:
        result = cache.get(key)
    except (RedisError, OSError):
        result = None
    if result is None:
        result = build_state(user)
        try:
            cache.set(key, result, 900)
        except (RedisError, OSError):
            log.warning("state_cache_unavailable")
    return Response(result)


@api_view(["GET"])
@permission_classes([CoachOnly])
def oversight(request):
    # Personal drill-down and collective comparisons use server-authorized data.
    since = timezone.localdate() - timedelta(days=6)
    people = m.User.objects.filter(is_active=True, is_coach=False)
    if team := request.query_params.get("team"):
        people = people.filter(team=team)
    if ring := request.query_params.get("ring"):
        people = people.filter(ring=ring)
    if code := request.query_params.get("person"):
        people = people.filter(code=code)
    metric = request.query_params.get("metric", "sport")
    if metric not in ("sport", "reading", "attendance", "activity"):
        raise ValidationError("شاخص معتبر نیست.")
    growth_totals = {
        item["actor_id"]: item for item in
        m.Growth.objects.filter(day__gte=since, actor__in=people).values("actor_id").annotate(sport=Sum("sport"), reading=Sum("reading"))
    }
    activity_counts = dict(
        visible_posts().filter(actor__in=people, created__date__gte=since).values("actor_id").annotate(n=Count("id")).values_list("actor_id", "n")
    )
    attendance_values = dict(m.Preference.objects.filter(actor__in=people, name="attendance").values_list("actor_id", "value"))
    rows = []
    for user in people[:2000]:
        aggregate = growth_totals.get(user.pk, {})
        snapshot = attendance_values.get(user.pk, {})
        percent = snapshot.get("percent") if snapshot.get("status") == "ok" else None
        value = {"sport": aggregate.get("sport", 0), "reading": aggregate.get("reading", 0),
                 "attendance": percent, "activity": activity_counts.get(user.pk, 0)}[metric]
        rows.append({"code": user.code, "name": user.name, "ring": user.ring, "group": user.team, "value": value})
    programs = post_queryset(request.user).filter(payload__type__in=["حلقه", "کارگروه"])
    reports = []
    if code := request.query_params.get("person"):
        reports = [dict(g.payload, userId=g.actor_id, day=g.day.isoformat())
                   for g in m.Growth.objects.filter(actor_id=code, day__gte=since)[:7]]
    return Response({"rows": rows, "reports": reports,
                     "programs": [post_output(p, request.user) for p in programs[:200]]})



@api_view(["POST"])
def assistant_chat(request):
    text = validated(s.QuestionInput, request)["message"]
    if re.search("سلام|خوبی|چطوری|ممنون", text) and not re.search("ورزش|مطالعه|گزارش|رشد", text):
        return Response({"text": "سلام! خوش آمدی. می‌توانم گزارش رشد تو و هم‌حلقه‌ای‌هایت را مرور کنم یا مسیر بخش‌های سایت را نشان بدهم."})
    guides = [
        ("مصوبه|پروفایل|کتاب.*کجا", "برنامه و کتابت را در پروفایل، بخش وضعیت من می‌بینی.", "/profile/"),
        ("پست.*کجا|پست.*چطور", "برای اشتراک‌گذاری، در صفحهٔ پست‌ها «پست جدید» را بزن.", "/posts/"),
        ("ثبت.*کجا|فرم.*چطور|رشد.*کجا", "ورزش، مطالعه و مهارت امروزت را در صفحهٔ رشد فردی ثبت کن.", "/growth/"),
    ]
    for pattern, answer, route in guides:
        if re.search(pattern, text):
            return Response({"text": answer, "route": route})
    if not re.search("ورزش|مطالعه|گزارش|رشد|آمار|ثبت", text):
        return Response({"text": "می‌توانم دربارهٔ آمار رشد خودت و حلقه‌ات یا راهنمای بخش‌های اخوت کمک کنم."})
    fallback = {"kind": "stats", "scope": "self", "period":
                "compare" if "مقایسه" in text else "previous" if "هفته قبل" in text else
                "yesterday" if "دیروز" in text else "today" if "امروز" in text else "week"}
    if re.search("حلقه|بچه|اعضا", text):
        fallback["scope"] = "peers" if "هم‌حلقه" in text or "هم حلقه" in text else "ring"
    plan = interpret(text, fallback)
    if plan["kind"] != "stats":
        return Response({"text": "برای تحلیل، دربارهٔ ورزش، مطالعه یا گزارش‌های خودت و حلقه‌ات بپرس."})
    members = m.User.objects.filter(pk=request.user.pk)
    if plan["scope"] != "self":
        if not request.user.ring:
            return Response({"text": "هنوز حلقه‌ای برای حسابت مشخص نشده است."})
        members = m.User.objects.filter(ring=request.user.ring)
        if plan["scope"] == "peers":
            members = members.exclude(pk=request.user.pk)
    period = plan["period"]
    results = []
    for start, end in periods(period, timezone.localdate()):
        rows = m.Growth.objects.filter(actor__in=members, day__range=(start, end))
        totals = rows.aggregate(sport=Sum("sport"), reading=Sum("reading"))
        results.append(f'{rows.count()} گزارش، {totals["sport"] or 0:g} ساعت ورزش و {totals["reading"] or 0} صفحه مطالعه')
    return Response({"text": "آمار بازهٔ انتخاب‌شده\n" + "\n".join(results)})


@api_view(["POST"])
def landing(request):
    if not request.user.is_workgroup_manager or not request.user.team:
        raise PermissionDenied()
    data = validated(s.LandingInput, request)
    item = m.LandingContent.objects.create(author=request.user, team=request.user.team, **data)
    return Response({"id": item.id}, status=201)


@api_view(["POST"])
def forms(request):
    if not request.user.is_workgroup_manager or not request.user.team:
        raise PermissionDenied()
    item = m.CustomForm.objects.create(author=request.user, team=request.user.team, **validated(s.FormInput, request))
    return Response({"id": item.id}, status=201)


@api_view(["PUT", "GET"])
def form_answers(request, fid):
    form = get_object_or_404(m.CustomForm, pk=fid)
    if request.method == "GET":
        if form.author_id != request.user.pk and not request.user.is_coach:
            raise PermissionDenied()
        return Response(list(m.FormResponse.objects.filter(form=form).values("actor__name", "answers")))
    answers = validated(s.AnswersInput, request)["answers"]
    if not isinstance(answers, list) or len(answers) != len(form.questions) or any(not isinstance(a, str) or len(a) > 4000 for a in answers):
        raise ValidationError("پاسخ‌های فرم معتبر نیست.")
    m.FormResponse.objects.update_or_create(form=form, actor=request.user, defaults={"answers": answers})
    return Response({"ok": True})


@api_view(["GET"])
@permission_classes([AdminOnly])
def weekly(request):
    start, end = periods("week", timezone.localdate())[0]
    people = m.User.objects.filter(is_active=True, is_coach=False)
    counts = dict(m.Growth.objects.filter(day__range=(start, end)).values("actor_id").annotate(n=Count("day")).values_list("actor_id", "n"))
    rows = [{"code": u.code, "name": u.name, "nights": counts.get(u.code, 0)} for u in people]
    programs = visible_posts().filter(created__date__range=(start, end))
    return Response({"members": rows,
                     "rings": list(programs.filter(payload__type="حلقه").values("actor__ring").annotate(count=Count("id"))),
                     "groups": list(programs.filter(payload__type="کارگروه").values("actor__team").annotate(count=Count("id")))})


@api_view(["PUT"])
@permission_classes([AdminOnly])
def roles(request, code):
    data = validated(s.RoleInput, request)
    with transaction.atomic():
        # Lock administrator rows to prevent concurrent removal of the last admin.
        list(m.User.objects.filter(is_admin=True).select_for_update().values_list("pk", flat=True))
        user = get_object_or_404(m.User.objects.select_for_update(), pk=code)
        if user.is_admin and not data["is_admin"] and not m.User.objects.filter(is_admin=True, is_active=True).exclude(pk=user.pk).exists():
            raise ValidationError("حداقل یک ادمین فعال باید باقی بماند.")
        for field, value in data.items():
            setattr(user, field, value)
        user.save(update_fields=list(data))
        audit(request.user, "roles_changed", code)
    return Response(s.UserOutput(user).data)


@api_view(["GET"])
def member_profile(request, code):
    user = get_object_or_404(m.User, pk=code, is_active=True)
    avatar = m.Preference.objects.filter(actor=user, name="avatar").first()
    return Response({
        "code": user.code, "name": user.name, "avatar": avatar.value if avatar else "",
        "posts": visible_posts().filter(actor=user).count(),
        "followers": m.Follow.objects.filter(target=user).count(),
        "following": m.Follow.objects.filter(actor=user).count(),
    })


@api_view(["GET"])
def rankings(request):
    members = m.User.objects.filter(is_active=True).exclude(ring="")
    scores = {}
    snapshots = dict(m.Preference.objects.filter(actor__in=members, name="attendance").values_list("actor_id", "value"))
    growth_totals = {row["actor_id"]: row for row in m.Growth.objects.filter(actor__in=members)
                     .values("actor_id").annotate(sport=Sum("sport"), reading=Sum("reading"))}
    post_counts = dict(visible_posts().filter(actor__in=members).values("actor_id")
                       .annotate(n=Count("id")).values_list("actor_id", "n"))
    for member in members:
        bucket = scores.setdefault(member.ring, {"attendance_sum": 0, "attendance_count": 0, "activity": 0})
        snapshot = snapshots.get(member.pk, {})
        if snapshot.get("status") == "ok" and snapshot.get("percent") is not None:
            bucket["attendance_sum"] += snapshot["percent"]
            bucket["attendance_count"] += 1
        growth = growth_totals.get(member.pk, {})
        bucket["activity"] += (growth.get("sport") or 0) + (growth.get("reading") or 0) + post_counts.get(member.pk, 0)
    external_likes = m.Vote.objects.filter(kind="like", post__in=visible_posts().filter(payload__type="حلقه")).select_related("post__actor", "actor")
    for like in external_likes.iterator():
        ring = like.post.payload.get("ring") or like.post.actor.ring
        if ring in scores and like.actor.ring != ring:
            scores[ring]["activity"] += 1
    grades = dict(m.Grade.objects.filter(kind="ring").values_list("target", "score"))
    result = []
    for name, values in scores.items():
        attendance_value = values["attendance_sum"] / values["attendance_count"] if values["attendance_count"] else None
        coach_score = grades.get(name, 0)
        result.append({"name": name, "attendance": attendance_value, "coach": coach_score,
                       "activity": values["activity"],
                       "total": 2 * coach_score + 2 * (attendance_value or 0) + values["activity"]})
    return Response(sorted(result, key=lambda row: (-row["total"], row["name"])))
