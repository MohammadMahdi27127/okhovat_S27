from uuid import uuid4
from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone


def identifier():
    return uuid4().hex


class UserManager(BaseUserManager):
    def create_user(self, code, password=None, **fields):
        user = self.model(code=code, **fields)
        user.set_password(password)
        user.full_clean(exclude=["last_login"])
        user.save(using=self._db)
        return user

    def create_superuser(self, code, password, **fields):
        fields["is_admin"] = True
        return self.create_user(code, password, **fields)


class User(AbstractBaseUser):
    password = models.CharField("هش رمز عبور", max_length=256)
    code = models.CharField("کد گروهی", max_length=40, primary_key=True,
                            validators=[RegexValidator(r"^[0-9]+$")])
    name = models.CharField("نام", max_length=120)
    ring = models.CharField("حلقه", max_length=120, blank=True)
    team = models.CharField("کارگروه", max_length=120, blank=True)
    is_coach = models.BooleanField("مربی", default=False)
    is_admin = models.BooleanField("ادمین", default=False)
    is_ring_leader = models.BooleanField("مسئول حلقه", default=False)
    is_workgroup_manager = models.BooleanField("مسئول کارگروه", default=False)
    is_concerned_member = models.BooleanField("عضو دغدغه‌مند", default=False)
    is_active = models.BooleanField("فعال", default=True)
    suspended_until = models.DateTimeField("پایان تعلیق", null=True, blank=True)
    bale_id = models.CharField("شناسه بله", max_length=100, blank=True)
    objects = UserManager()
    USERNAME_FIELD = "code"
    REQUIRED_FIELDS = ["name"]

    @property
    def suspended(self):
        return bool(self.suspended_until and self.suspended_until > timezone.now())

    class Meta:
        db_table = "ok_accounts"
        ordering = ["name", "code"]
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"


class Growth(models.Model):
    pk = models.CompositePrimaryKey("actor_id", "day")
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.CASCADE, verbose_name="عضو")
    day = models.DateField("تاریخ")
    sport = models.FloatField("ساعت ورزش", validators=[MinValueValidator(0), MaxValueValidator(24)])
    reading = models.IntegerField("صفحه مطالعه", validators=[MinValueValidator(0), MaxValueValidator(10000)])
    payload = models.JSONField("جزئیات گزارش", default=dict)
    class Meta:
        db_table = "ok_growth"
        ordering = ["-day", "actor_id"]
        verbose_name = "گزارش رشد"
        indexes = [models.Index(fields=["day", "actor"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(sport__gte=0, sport__lte=24), name="growth_sport_range"),
            models.CheckConstraint(condition=models.Q(reading__gte=0, reading__lte=10000), name="growth_reading_range"),
        ]


class Post(models.Model):
    id = models.CharField("شناسه", max_length=65, primary_key=True, default=identifier)
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.PROTECT, verbose_name="نویسنده")
    created = models.DateTimeField("زمان ثبت", default=timezone.now)
    payload = models.JSONField("محتوا", default=dict)
    class Meta:
        db_table = "ok_posts"
        ordering = ["-created", "-id"]
        verbose_name = "پست"


class Vote(models.Model):
    pk = models.CompositePrimaryKey("post_id", "actor_id", "kind")
    post = models.ForeignKey(Post, db_column="post", on_delete=models.CASCADE, verbose_name="پست")
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.CASCADE, verbose_name="عضو")
    kind = models.CharField("نوع", max_length=12, choices=[("like", "پسند"), ("recommend", "پیشنهاد به مربی"), ("bookmark", "ذخیره")])
    class Meta:
        db_table = "ok_votes"
        verbose_name = "واکنش"
        ordering = ["post_id", "actor_id", "kind"]


class Comment(models.Model):
    id = models.CharField("شناسه", max_length=65, primary_key=True, default=identifier)
    post = models.ForeignKey(Post, db_column="post", on_delete=models.CASCADE, verbose_name="پست")
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.PROTECT, verbose_name="نویسنده")
    parent = models.ForeignKey("self", db_column="parent", null=True, blank=True, on_delete=models.CASCADE, verbose_name="پاسخ به")
    body = models.TextField("متن")
    created = models.DateTimeField("زمان ثبت", default=timezone.now)
    class Meta:
        db_table = "ok_comments"
        ordering = ["created", "id"]
        verbose_name = "دیدگاه"


class CommentLike(models.Model):
    pk = models.CompositePrimaryKey("comment_id", "actor_id")
    comment = models.ForeignKey(Comment, db_column="id", on_delete=models.CASCADE, verbose_name="دیدگاه")
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.CASCADE, verbose_name="عضو")
    class Meta:
        db_table = "ok_comment_likes"
        verbose_name = "پسند دیدگاه"


class Message(models.Model):
    id = models.CharField("شناسه", max_length=65, primary_key=True, default=identifier)
    sender = models.ForeignKey(User, db_column="sender", on_delete=models.PROTECT, verbose_name="فرستنده")
    label = models.CharField("مخاطبان", max_length=200)
    body = models.TextField("متن")
    created = models.DateTimeField("زمان ارسال", default=timezone.now)
    class Meta:
        db_table = "ok_messages"
        ordering = ["-created", "-id"]
        verbose_name = "پیام مربی"


class Inbox(models.Model):
    pk = models.CompositePrimaryKey("message_id", "actor_id")
    message = models.ForeignKey(Message, db_column="message", on_delete=models.CASCADE, verbose_name="پیام")
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.CASCADE, verbose_name="گیرنده")
    seen = models.BooleanField("خوانده‌شده", default=False)
    class Meta:
        db_table = "ok_inbox"
        verbose_name = "صندوق پیام"


class Grade(models.Model):
    pk = models.CompositePrimaryKey("kind", "target")
    kind = models.CharField("نوع", max_length=12, choices=[("ring", "حلقه"), ("group", "کارگروه")])
    target = models.CharField("نام", max_length=120)
    score = models.FloatField("امتیاز", validators=[MinValueValidator(0)])
    coach = models.ForeignKey(User, db_column="coach", on_delete=models.PROTECT, verbose_name="مربی")
    class Meta:
        db_table = "ok_grades"
        verbose_name = "امتیاز مربی"


class Preference(models.Model):
    pk = models.CompositePrimaryKey("actor_id", "name")
    actor = models.ForeignKey(User, db_column="actor", on_delete=models.CASCADE, verbose_name="عضو")
    name = models.CharField("تنظیم", max_length=100)
    value = models.JSONField("مقدار", default=dict)
    class Meta:
        db_table = "ok_preferences"
        verbose_name = "تنظیم کاربر"


class File(models.Model):
    id = models.CharField("شناسه", max_length=65, primary_key=True, default=identifier)
    owner = models.ForeignKey(User, db_column="owner", on_delete=models.PROTECT, verbose_name="مالک")
    purpose = models.CharField("کاربرد", max_length=12, choices=[("avatar", "آواتار"), ("proof", "مستند رشد"), ("post", "پیوست پست")])
    name = models.CharField("نام فایل", max_length=255)
    mime = models.CharField("نوع محتوا", max_length=100)
    uploaded_at = models.DateTimeField("زمان بارگذاری", default=timezone.now, db_index=True)
    size_bytes = models.BigIntegerField("حجم واقعی فایل", default=0)
    quota_bytes = models.BigIntegerField("حجم محاسبه‌شده در سهمیه", default=0)
    class Meta:
        db_table = "ok_files"
        verbose_name = "فایل"


class UploadUsage(models.Model):
    actor = models.OneToOneField(User, db_column="actor", primary_key=True, on_delete=models.CASCADE, verbose_name="عضو")
    used = models.BigIntegerField("حجم مصرفی", default=0)
    class Meta:
        db_table = "ok_upload_usage"
        verbose_name = "مصرف فضای فایل"


class Notice(models.Model):
    id = models.CharField("شناسه", max_length=100, primary_key=True, default=identifier)
    recipient = models.ForeignKey(User, db_column="recipient", on_delete=models.CASCADE, verbose_name="گیرنده")
    kind = models.CharField("نوع اعلان", max_length=20)
    created = models.DateTimeField("زمان", default=timezone.now)
    seen = models.BooleanField("خوانده‌شده", default=False)
    class Meta:
        db_table = "ok_notices"
        ordering = ["-created"]
        verbose_name = "اعلان"


class Follow(models.Model):
    pk = models.CompositePrimaryKey("actor_id", "target_id")
    actor = models.ForeignKey(User, db_column="actor", related_name="following", on_delete=models.CASCADE, verbose_name="دنبال‌کننده")
    target = models.ForeignKey(User, db_column="target", related_name="followers", on_delete=models.CASCADE, verbose_name="دنبال‌شونده")
    class Meta:
        db_table = "ok_follows"
        verbose_name = "دنبال‌کردن"
        constraints = [models.CheckConstraint(condition=~models.Q(actor=models.F("target")), name="no_self_follow")]


class RemovedPost(models.Model):
    post = models.OneToOneField(Post, db_column="post", primary_key=True, on_delete=models.CASCADE, verbose_name="پست")
    moderator = models.ForeignKey(User, db_column="moderator", on_delete=models.PROTECT, verbose_name="ادمین")
    removed_at = models.DateTimeField("زمان حذف", default=timezone.now)
    media = models.CharField("فایل", max_length=150, blank=True)
    class Meta:
        db_table = "ok_removed_posts"
        verbose_name = "حذف مدیریتی"


class Revision(models.Model):
    id = models.IntegerField(primary_key=True)
    rev = models.CharField("نسخه داده", max_length=32, default=identifier)
    class Meta:
        db_table = "ok_revision"
        verbose_name = "نسخه داده"


class LandingContent(models.Model):
    id = models.CharField("شناسه", max_length=32, primary_key=True, default=identifier)
    author = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="مسئول")
    team = models.CharField("کارگروه", max_length=120)
    title = models.CharField("عنوان", max_length=200)
    body = models.TextField("توضیح")
    created = models.DateTimeField("زمان", default=timezone.now)
    class Meta:
        db_table = "ok_landing"
        ordering = ["-created"]
        verbose_name = "محتوای کارگروه"


class CustomForm(models.Model):
    id = models.CharField("شناسه", max_length=32, primary_key=True, default=identifier)
    author = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="سازنده")
    team = models.CharField("کارگروه", max_length=120)
    title = models.CharField("عنوان", max_length=200)
    questions = models.JSONField("پرسش‌ها", default=list)
    class Meta:
        db_table = "ok_forms"
        verbose_name = "فرم کارگروه"


class FormResponse(models.Model):
    form = models.ForeignKey(CustomForm, on_delete=models.CASCADE, verbose_name="فرم")
    actor = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="عضو")
    answers = models.JSONField("پاسخ‌ها", default=list)
    class Meta:
        db_table = "ok_form_responses"
        verbose_name = "پاسخ فرم"
        constraints = [models.UniqueConstraint(fields=["form", "actor"], name="one_form_response")]


class AuditEvent(models.Model):
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, verbose_name="عامل")
    action = models.CharField("عملیات", max_length=40)
    target = models.CharField("هدف", max_length=100, blank=True)
    created = models.DateTimeField("زمان", default=timezone.now)
    class Meta:
        db_table = "ok_audit"
        ordering = ["-created"]
        verbose_name = "رویداد امنیتی"
