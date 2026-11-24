from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("core", "0002_alter_user_password")]

    operations = [
        migrations.AddField(
            model_name="file", name="uploaded_at",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="زمان بارگذاری"),
        ),
        migrations.AddField(
            model_name="file", name="size_bytes",
            field=models.BigIntegerField(default=0, verbose_name="حجم واقعی فایل"),
        ),
        migrations.AddField(
            model_name="file", name="quota_bytes",
            field=models.BigIntegerField(default=0, verbose_name="حجم محاسبه‌شده در سهمیه"),
        ),
    ]
