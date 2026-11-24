import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_file_storage_metadata"),
    ]

    operations = [
        # Expand File.purpose choices to include "landing"
        migrations.AlterField(
            model_name="file",
            name="purpose",
            field=models.CharField(
                choices=[
                    ("avatar", "آواتار"),
                    ("proof", "مستند رشد"),
                    ("post", "پیوست پست"),
                    ("landing", "محتوای لندینگ"),
                ],
                max_length=12,
                verbose_name="کاربرد",
            ),
        ),
        # New LandingCard model
        migrations.CreateModel(
            name="LandingCard",
            fields=[
                ("id", models.CharField(max_length=32, primary_key=True, serialize=False, verbose_name="شناسه")),
                ("team", models.CharField(max_length=120, verbose_name="کارگروه")),
                ("card_type", models.CharField(
                    choices=[
                        ("announcement", "اطلاعیه"),
                        ("meeting", "جلسه"),
                        ("image", "تصویر"),
                        ("html", "HTML"),
                        ("debtors", "بدهکاران"),
                        ("wanted", "وانتد"),
                        ("offenders", "متخلفین"),
                        ("gym_offenders", "متخلفین باشگاه"),
                    ],
                    max_length=20,
                    verbose_name="نوع کارت",
                )),
                ("title", models.CharField(default="اطلاعیه", max_length=200, verbose_name="عنوان")),
                ("body", models.TextField(blank=True, verbose_name="متن")),
                ("meeting_at", models.DateTimeField(blank=True, null=True, verbose_name="زمان جلسه")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("created", models.DateTimeField(default=django.utils.timezone.now, verbose_name="زمان ایجاد")),
                ("updated", models.DateTimeField(auto_now=True, verbose_name="زمان ویرایش")),
                ("author", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    to="core.user",
                    verbose_name="مسئول",
                )),
                ("html_file", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="core.file",
                    verbose_name="فایل HTML",
                )),
                ("image", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="core.file",
                    verbose_name="تصویر",
                )),
            ],
            options={
                "verbose_name": "کارت لندینگ",
                "db_table": "ok_landing_cards",
                "ordering": ["team"],
            },
        ),
        migrations.AddConstraint(
            model_name="landingcard",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("team",),
                name="one_active_landing_card_per_team",
            ),
        ),
        # New MemberTitle model
        migrations.CreateModel(
            name="MemberTitle",
            fields=[
                ("id", models.CharField(max_length=32, primary_key=True, serialize=False, verbose_name="شناسه")),
                ("kind", models.CharField(
                    choices=[
                        ("debtor", "بدهکار"),
                        ("wanted", "وانتد"),
                        ("offender", "متخلف"),
                        ("gym_offender", "متخلف باشگاه"),
                    ],
                    max_length=20,
                    verbose_name="نوع عنوان",
                )),
                ("team", models.CharField(max_length=120, verbose_name="کارگروه ثبت‌کننده")),
                ("week_start", models.DateField(verbose_name="شروع هفته")),
                ("created", models.DateTimeField(default=django.utils.timezone.now, verbose_name="زمان ثبت")),
                ("actor", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="titles",
                    to="core.user",
                    verbose_name="عضو",
                )),
                ("registered_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="+",
                    to="core.user",
                    verbose_name="ثبت‌کننده",
                )),
                ("wanted_poster", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="+",
                    to="core.file",
                    verbose_name="پوستر وانتد",
                )),
            ],
            options={
                "verbose_name": "عنوان عضو",
                "db_table": "ok_member_titles",
                "ordering": ["-created"],
            },
        ),
        migrations.AddIndex(
            model_name="membertitle",
            index=models.Index(fields=["kind", "week_start"], name="ok_member_t_kind_week_idx"),
        ),
        migrations.AddIndex(
            model_name="membertitle",
            index=models.Index(fields=["actor", "kind"], name="ok_member_t_actor_kind_idx"),
        ),
        migrations.AddIndex(
            model_name="membertitle",
            index=models.Index(fields=["team", "kind", "week_start"], name="ok_member_t_team_kind_week_idx"),
        ),
    ]
