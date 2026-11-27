"""Landing cards and member titles API helpers + views."""
from datetime import timedelta
from pathlib import Path

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied

from . import models as m, serializers as s
from .storage import storage_dir, file_path
from .wanted import make_wanted_poster
from .security import require_csrf


def week_start_for(day=None):
    """Return the Saturday that starts the Iranian week containing *day*."""
    day = day or timezone.localdate()
    # In Iran week starts on Saturday. Python: Monday=0 ... Sunday=6
    # Saturday = 5
    offset = (day.weekday() - 5) % 7
    return day - timedelta(days=offset)


def require_workgroup_manager(user):
    if not user.is_authenticated or not user.is_workgroup_manager or not user.team:
        raise PermissionDenied("فقط مسئول کارگروه می‌تواند این عملیات را انجام دهد.")
    if user.team not in m.KNOWN_TEAMS:
        raise PermissionDenied("کارگروه شما در فهرست شناخته‌شده نیست.")
    return user.team


def card_output(card):
    data = {
        "id": card.id,
        "team": card.team,
        "card_type": card.card_type,
        "title": card.title,
        "body": card.body,
        "meeting_at": card.meeting_at.isoformat() if card.meeting_at else None,
        "image": f"/api/files/{card.image_id}/" if card.image_id else None,
        "html_file": f"/api/files/{card.html_file_id}/" if card.html_file_id else None,
        "updated": card.updated.isoformat(),
        "author_name": card.author.name,
    }
    return data


def title_output(row):
    return {
        "id": row.id,
        "actor_code": row.actor_id,
        "actor_name": row.actor.name,
        "kind": row.kind,
        "team": row.team,
        "week_start": row.week_start.isoformat(),
        "wanted_poster": f"/api/files/{row.wanted_poster_id}/" if row.wanted_poster_id else None,
        "created": row.created.isoformat(),
    }


# ---------------------------------------------------------------------------
# Serializers (local, kept close to the views)
# ---------------------------------------------------------------------------
from rest_framework import serializers


class LandingCardInput(s.StrictSerializer):
    card_type = serializers.ChoiceField(choices=[c[0] for c in m.LandingCard.CARD_TYPES])
    title = serializers.CharField(max_length=200, default="اطلاعیه")
    body = serializers.CharField(max_length=8000, allow_blank=True, default="")
    meeting_at = serializers.DateTimeField(required=False, allow_null=True)
    image = serializers.CharField(max_length=100, allow_blank=True, default="")
    html_file = serializers.CharField(max_length=100, allow_blank=True, default="")


class TitleInput(s.StrictSerializer):
    actor_code = serializers.RegexField(r"^[0-9]{1,40}$", max_length=40)
    kind = serializers.ChoiceField(choices=[c[0] for c in m.MemberTitle.KINDS])
    week_start = serializers.DateField(required=False)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([AllowAny])
def landing_cards(request):
    """Public list of all currently active landing cards."""
    rows = (
        m.LandingCard.objects
        .filter(is_active=True)
        .select_related("author", "image", "html_file")
        .order_by("team")
    )
    return Response([card_output(c) for c in rows])


@api_view(["POST", "PUT", "DELETE"])
def manage_landing_card(request):
    """Create / update / deactivate the active card for the manager's own team."""
    team = require_workgroup_manager(request.user)
    require_csrf(request._request)

    if request.method == "DELETE":
        updated = m.LandingCard.objects.filter(team=team, is_active=True).update(is_active=False)
        return Response({"ok": True, "deactivated": updated})

    data = LandingCardInput(data=request.data)
    data.is_valid(raise_exception=True)
    payload = data.validated_data

    # Validate card_type against team capabilities
    allowed = {
        "مالی": {"announcement", "debtors"},
        "هدایت و برنامه ریزی": {"announcement", "meeting", "html"},
        "آموزش": {"announcement"},
        "خدمات": {"announcement", "image"},
        "علوم اسلامی": {"announcement", "image"},
        "فرهنگی": {"announcement", "image"},
        "سازماندهی": {"announcement", "offenders"},
        "پذیرش": {"announcement", "wanted"},
        "تربیت بدنی": {"announcement", "gym_offenders"},
        "تدارکات": {"announcement", "image"},
    }
    if payload["card_type"] not in allowed.get(team, set()):
        raise ValidationError(f"نوع کارت «{payload['card_type']}» برای کارگروه «{team}» مجاز نیست.")

    image_file = None
    html_file = None
    if payload.get("image"):
        match = __import__("re").fullmatch(r"/api/files/([a-f0-9]{32})/", payload["image"])
        if not match:
            raise ValidationError("نشانی تصویر معتبر نیست.")
        image_file = get_object_or_404(m.File, pk=match[1], owner=request.user, purpose="landing")
    if payload.get("html_file"):
        match = __import__("re").fullmatch(r"/api/files/([a-f0-9]{32})/", payload["html_file"])
        if not match:
            raise ValidationError("نشانی فایل HTML معتبر نیست.")
        html_file = get_object_or_404(m.File, pk=match[1], owner=request.user, purpose="landing")

    if payload["card_type"] == "meeting" and not payload.get("meeting_at"):
        raise ValidationError("برای کارت جلسه باید تاریخ و ساعت مشخص شود.")
    if payload["card_type"] == "image" and not image_file:
        raise ValidationError("برای کارت تصویری باید عکس بارگذاری شود.")
    if payload["card_type"] == "html" and not html_file:
        raise ValidationError("برای کارت HTML باید فایل بارگذاری شود.")

    with transaction.atomic():
        # Deactivate any previous active card for this team
        m.LandingCard.objects.filter(team=team, is_active=True).update(is_active=False)
        card = m.LandingCard.objects.create(
            team=team,
            author=request.user,
            card_type=payload["card_type"],
            title=payload["title"],
            body=payload["body"],
            meeting_at=payload.get("meeting_at"),
            image=image_file,
            html_file=html_file,
            is_active=True,
        )
    return Response(card_output(card), status=201)


@api_view(["GET"])
def landing_titles(request):
    """List titles for a given kind (optionally filtered by week)."""
    kind = request.query_params.get("kind")
    if kind not in dict(m.MemberTitle.KINDS):
        raise ValidationError("نوع عنوان معتبر نیست.")
    qs = m.MemberTitle.objects.filter(kind=kind).select_related("actor", "wanted_poster")
    week = request.query_params.get("week")
    if week:
        qs = qs.filter(week_start=week)
    elif request.query_params.get("all"):
        pass  # کل تاریخچه: برای محاسبهٔ تعداد دفعات قبلی
    else:
        # default: current week
        qs = qs.filter(week_start=week_start_for())
    return Response([title_output(r) for r in qs.order_by("actor__name")])


@api_view(["POST"])
def add_title(request):
    """Register a member title (debtor / wanted / offender / gym_offender)."""
    team = require_workgroup_manager(request.user)
    require_csrf(request._request)
    data = TitleInput(data=request.data)
    data.is_valid(raise_exception=True)
    payload = data.validated_data

    kind_to_team = {
        "debtor": "مالی",
        "wanted": "پذیرش",
        "offender": "سازماندهی",
        "gym_offender": "تربیت بدنی",
    }
    if kind_to_team.get(payload["kind"]) != team:
        raise PermissionDenied("این نوع عنوان متعلق به کارگروه شما نیست.")

    actor = get_object_or_404(m.User, pk=payload["actor_code"], is_active=True)
    ws = payload.get("week_start") or week_start_for()

    # Prevent exact duplicate in the same week
    if m.MemberTitle.objects.filter(actor=actor, kind=payload["kind"], week_start=ws).exists():
        raise ValidationError("این عنوان برای این عضو در هفته جاری قبلاً ثبت شده است.")

    poster_file = None
    if payload["kind"] == "wanted":
        # Build Wanted poster
        avatar_pref = m.Preference.objects.filter(actor=actor, name="avatar").first()
        avatar_path = None
        if avatar_pref and isinstance(avatar_pref.value, str):
            import re
            match = re.fullmatch(r"/api/files/([a-f0-9]{32})/", avatar_pref.value)
            if match:
                try:
                    av_file = m.File.objects.get(pk=match[1])
                    avatar_path = file_path(av_file)
                except m.File.DoesNotExist:
                    pass
        jpeg_bytes = make_wanted_poster(avatar_path, actor.name)
        from .models import identifier
        fid = identifier()
        charge = max(len(jpeg_bytes), 4096)
        dest = storage_dir("landing") / fid
        try:
            with transaction.atomic():
                # Charge the generated poster to the registrant's quota so that
                # remove_title releasing the same amount stays balanced.
                m.User.objects.select_for_update().get(pk=request.user.pk)
                usage, _ = m.UploadUsage.objects.get_or_create(actor=request.user)
                if usage.used + charge > 256 * 1024 * 1024:
                    raise ValidationError("سهمیهٔ فایل این حساب تکمیل شده است.")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(jpeg_bytes)
                poster_file = m.File.objects.create(
                    id=fid,
                    owner=request.user,
                    purpose="landing",
                    name=f"wanted-{actor.code}.jpg",
                    mime="image/jpeg",
                    size_bytes=len(jpeg_bytes),
                    quota_bytes=charge,
                )
                usage.used += charge
                usage.save(update_fields=["used"])
        except Exception:
            dest.unlink(missing_ok=True)
            raise

    row = m.MemberTitle.objects.create(
        actor=actor,
        kind=payload["kind"],
        team=team,
        registered_by=request.user,
        week_start=ws,
        wanted_poster=poster_file,
    )
    return Response(title_output(row), status=201)


@api_view(["DELETE"])
def remove_title(request, tid):
    """Remove a previously registered title (manager of the same team only)."""
    team = require_workgroup_manager(request.user)
    require_csrf(request._request)
    row = get_object_or_404(m.MemberTitle, pk=tid)
    if row.team != team:
        raise PermissionDenied("این عنوان متعلق به کارگروه شما نیست.")
    # Optionally delete the poster file
    if row.wanted_poster_id:
        from .storage import delete_file_and_release_quota
        delete_file_and_release_quota(row.wanted_poster_id)
    row.delete()
    return Response({"ok": True})
