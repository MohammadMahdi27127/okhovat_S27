# اخوت — React + Django REST Framework

این نسخه در پوشه‌ای مستقل از پروژهٔ قبلی ساخته شده است. رابط React با TypeScript و Framer Motion، API با Django/DRF، دیتابیس PostgreSQL و کش Redis کار می‌کنند. Dockerfile برای اجرای React، Django و Redis در یک اپ اضافه شده است؛ PostgreSQL جداست و حساب پیش‌فرض وجود ندارد.

برای استقرار در **دارکوب** ابتدا [docs/DARKUBE.md](docs/DARKUBE.md) را بخوان. راهنمای زیر مربوط به اجرای دستی و لوکال است. در استقرار Docker، Redis داخل همان اپ است و اپ Redis جدا لازم نیست.

## ساختار

```text
backend/config/                  تنظیمات، مسیرها و نقطهٔ اجرای Django
backend/core/models.py           جدول‌ها و مدل کاربر
backend/core/serializers.py      اعتبارسنجی ورودی‌ها
backend/core/views.py            API و کنترل مالکیت داده‌ها
backend/core/security.py         کنترل دسترسی، محدودیت درخواست و هدرهای امنیتی
backend/core/management/commands دستور ساخت عضو، بازیابی رمز و انتقال داده
backend/core/migrations/         تغییرات نسخه‌بندی‌شدهٔ دیتابیس
frontend/src/pages/              صفحات React
frontend/src/components.tsx      اجزای مشترک، فرم، لودینگ و انیمیشن
frontend/src/legacy.css          استایل برگرفته از نسخهٔ قبلی
frontend/public/assets/          لوگو و تصاویر قبلی
docs/                           انتقال اطلاعات، API و گزارش بررسی
```

## پیش‌نیازها

- Python 3.12 و Node.js نسخهٔ 22.12 یا جدیدتر از شاخهٔ 22.
- PostgreSQL و Redis در دسترس دستگاه/سرور برنامه.
- یک دیتابیس PostgreSQL خالی و کاربری که اجازهٔ ساخت جدول در همان دیتابیس را دارد. برنامه هیچ نقش PostgreSQL از جمله `okhovat_web` نمی‌سازد.

## نصب لوکال در Windows PowerShell

۱. در پوشهٔ همین پروژه ترمینال باز کن و محیط پایتون بساز:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

۲. فایل `backend/.env` را باز کن. خروجی آخر را جای `SECRET_KEY` بگذار. مشخصات **واقعی دیتابیس و Redis خودت** را جایگزین کن:

```dotenv
DEBUG=True
SECRET_KEY=YOUR_GENERATED_SECRET
ALLOWED_HOSTS=localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
REDIS_URL=redis://:REDIS_PASSWORD@REDIS_HOST:6379/0
TRUST_PROXY_PROTO=False
```

اگر Redis محلی رمز ندارد: `redis://127.0.0.1:6379/0`. کاراکترهای رزروشدهٔ رمز در URL باید percent-encode شوند؛ رمز را در سایت‌های آنلاین encode نکن. فایل `.env` یا کلید Google را وارد Git نکن. آدرس داخلی دیتابیس سرویس‌دهنده معمولاً فقط از شبکهٔ همان سرویس‌دهنده قابل دسترسی است.

۳. جدول‌ها را بساز:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
```

۴. فقط برای دیتابیس تازه و بدون انتقال کاربران، حساب واقعی خودت را بساز. کد و نام نمونهٔ فرمان را با مشخصات خودت عوض کن. رمز در ترمینال مخفی پرسیده می‌شود:

```powershell
..\.venv\Scripts\python.exe manage.py create_member --code YOUR_NUMERIC_CODE --name "نام خودت" --admin
```

برای مربی از `--coach` استفاده کن. نقش‌ها هم‌زمان قابل انتخاب هستند؛ مثلاً `--admin --ring-leader --ring "سلمان"`. مسئول کارگروه: `--workgroup-manager --team "آموزش"`. هیچ کد و رمز ازپیش‌ساخته‌ای وجود ندارد. داده‌های تست فقط هنگام اجرای تست در دیتابیس موقت ساخته و حذف می‌شوند.

۵. API را اجرا کن:

```powershell
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

۶. یک PowerShell دوم، از پوشهٔ اصلی پروژه:

```powershell
cd frontend
npm ci
npm run dev
```

مرورگر را روی `http://127.0.0.1:5173` باز کن. Vite درخواست‌های `/api/` را به Django می‌فرستد. کوکی‌ها و CSRF از همین دامنه استفاده می‌کنند.

## اجرا روی سرور بدون Docker

روی Linux محیط مجازی را با `python3.12 -m venv .venv` بساز؛ دستورات Python از `.venv/bin/python` اجرا می‌شوند.

```bash
cd frontend
npm ci
npm run build
cd ../backend
../.venv/bin/python -m pip install -r requirements.txt
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py collectstatic --noinput
../.venv/bin/python manage.py check --deploy
../.venv/bin/gunicorn -c gunicorn.conf.py config.wsgi:application
```

`frontend/dist` باید کنار پوشهٔ `backend` روی سرور بماند. Django/WhiteNoise همین فایل‌های React را ارائه می‌دهد؛ فرانت و بک‌اند روی یک سرویس و دامنه اجرا می‌شوند. مسیرهای صفحات با React Router عوض می‌شوند و باز کردن مستقیمشان هم به `index.html` هدایت می‌شود. مسیر ناشناختهٔ `/api/` به API 404 می‌رسد، نه HTML.

در تنظیمات سرور:

- `DEBUG=False`، کلید تصادفی ثابت و خصوصی، `ALLOWED_HOSTS=example.com` و `CSRF_TRUSTED_ORIGINS=https://example.com`.
- HTTPS را فعال کن. `TRUST_PROXY_PROTO=True` فقط وقتی که پراکسی مورد اعتماد، هدر `X-Forwarded-Proto` را خودش بازنویسی می‌کند. در غیر این صورت فعالش نکن.
- برای تشخیص IP در محدودیت ورود، `TRUSTED_PROXY_COUNT` پیش‌فرض صفر است. پشت یک پراکسی که X-Forwarded-For را پاک‌سازی و بازنویسی می‌کند مقدار ۱ بگذار؛ تعداد را مطابق زنجیرهٔ واقعی تنظیم کن. هدر ارسال‌شده توسط کاربر نباید مبنای اعتماد باشد.
- پورت سرویس ۸۰۰۰، فرمان اجرا مطابق Gunicorn بالا، health endpoint برابر `/api/health/`. health فعلی سلامت Redis و PostgreSQL را نیز در مسیر درخواست بررسی می‌کند.
- `UPLOADS_DIR` را به دیسک دائمی خصوصی متصل کن. این پوشه نباید به‌صورت static/media عمومی در وب‌سرور ارائه شود؛ دانلود فقط از API مجاز است.
- اندازهٔ درخواست را در پراکسی حداکثر ۱۱ MiB و زمان انتظار را متناسب با timeout برنامه تنظیم کن. فایل هر درخواست حداکثر ۱۰ MiB است.
- فقط API وب عمومی شود؛ PostgreSQL و Redis در شبکهٔ خصوصی با رمز و دسترسی محدود بمانند. TLS دیتابیس را طبق الزام سرویس‌دهنده از طریق پارامتر `sslmode` تنظیم کن.
- migration را قبل از آغاز نسخهٔ جدید، یک بار اجرا کن. workerها خودکار جدول یا حساب نمی‌سازند.
- روزانه `python manage.py clearsessions` را با زمان‌بند سرور اجرا کن. از PostgreSQL و دیسک فایل‌ها نسخهٔ پشتیبان هماهنگ بگیر و بازیابی را آزمایش کن.

## نشست، کش و امنیت

Redis کش سمت سرور با TTL برابر ۹۰۰ ثانیه است؛ تغییر داده‌ها نسخهٔ کش را عوض می‌کند. نشست ورود در جدول استاندارد Django ذخیره می‌شود و ۷ روز اعتبار دارد؛ حذف کش Redis کاربر را خارج نمی‌کند. درخواست معمولی اعتبار را تمدید نمی‌کند؛ ورود دوباره زمان را از نو شروع می‌کند.

مرورگر مستقیماً به Redis متصل نیست. پاسخ API خصوصی `no-store` دارد و رمز یا توکن ورود در localStorage قرار نمی‌گیرد. localStorage فقط ترجیح ظاهر و تکمیل راهنمای ورود را نگه می‌دارد. فایل‌های ثابت حداکثر ۱۵ دقیقه کش می‌شوند.

رمز با Argon2 در ستون `ok_accounts.password` هش می‌شود. نقش‌ها Boolean مستقل هستند و دسترسی علاوه بر رابط، در API بررسی می‌شود. اطلاعات امنیتی بیشتر در [docs/REVIEW.md](docs/REVIEW.md).

## حضور و دستیار

در ورود با کد و رمز، حضور از همان Google Sheet و تب `643360414` خوانده می‌شود. در ساختار گروه‌بندی‌شدهٔ فعلی: ستون A کد گروهی، B نام، D درصد است. ردیف عنوان حلقه محدودهٔ اعضای حلقه را تعیین می‌کند. تطبیق با کد است، نه تشابه نام. خطای شبکه ورود را متوقف نمی‌کند؛ پروفایل خطای قابل‌فهم نشان می‌دهد. نشست موجود آخرین حضور دریافت‌شده را نمایش می‌دهد.

برای شیت خصوصی، service account فقط‌خواندنی بساز، شیت را با آن به اشتراک بگذار و مسیر JSON خصوصی را در `GOOGLE_APPLICATION_CREDENTIALS` تعیین کن. بدون آن، مسیر CSV فقط برای شیت قابل‌خواندن کار می‌کند.

دستیار پیش‌فرض پاسخ راهنما و آمار واقعی خود کاربر و حلقه‌اش می‌دهد؛ مدل زبانی آموزش‌دیدهٔ اختصاصی نیست. اتصال اختیاری Ollama با `ASSISTANT_OLLAMA_MODEL` و `ASSISTANT_OLLAMA_URL` فقط برای تشخیص قصد سؤال است؛ دسترسی به داده همچنان توسط سرور محدود می‌شود. اگر مدل قطع باشد، پاسخ آماری ساده برقرار می‌ماند. متن گفتگو ذخیره نمی‌شود.

## بازیابی رمز

صفحهٔ فراموشی رمز کاربر را به پشتیبانی هدایت می‌کند. پس از احراز هویت خارج از سامانه، مدیر سرور اجرا کند:

```bash
python manage.py reset_member_password --code NUMERIC_CODE
```

رمز مخفی پرسیده می‌شود؛ رمز در خط فرمان یا فایل قرار نمی‌گیرد. بازیابی خودکار از طریق پیام‌رسان/ایمیل فعال نیست، چون شناسهٔ تأییدشده و سرویس ارسال متصل نشده است.

## تست

```bash
cd backend
python manage.py test core --settings=config.test_settings
cd ../frontend
npm ci
npm test
npm run build
```

تست سریع از SQLite حافظه‌ای و کش حافظه‌ای **فقط در تنظیمات تست** استفاده می‌کند؛ تنظیمات اصلی صرفاً PostgreSQL را می‌پذیرند. برای بررسی واقعی PostgreSQL/Redis روی محیط آزمایشی مستقل، `DATABASE_URL` آزمایشی و `TEST_REDIS_URL` مربوط به Redis قابل‌حذف را تنظیم و اجرا کن:

```bash
python manage.py test core --settings=config.integration_test_settings
```

این تست دیتابیس `test_okhovat` را می‌سازد/حذف می‌کند و کش Redis انتخاب‌شده را پاک می‌کند؛ هرگز آن را به سرویس تولید یا Redis مشترک وصل نکن.

انتقال اطلاعات قبلی: [docs/MIGRATION.md](docs/MIGRATION.md). فهرست API: [docs/API.md](docs/API.md).
