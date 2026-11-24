# ممیزی فنی استقرار پروژهٔ اخوت (Okhovat) روی دارکوب

> وضعیت: **فقط ممیزی** — هیچ فایلی تغییر نکرده است. این سند هم گزارش ممیزی و هم برنامهٔ اصلاح مرحله‌به‌مرحله است.

---

## ۱. معماری کلی

| لایه | فناوری | محل در مخزن |
|---|---|---|
| فرانت‌اند | React + TypeScript + Vite + React Router | `frontend/` |
| بک‌اند | Django 5.2 + DRF | `backend/` |
| دیتابیس | PostgreSQL (سرویس جدا) | `backend/config/settings.py` (`DATABASE_URL`) |
| کش/نرخ‌محدودی | Redis محلی داخل همان کانتینر | `deploy/redis.conf` |
| سرور اپلیکیشن | Gunicorn (gthread) روی `0.0.0.0:8000` | `backend/gunicorn.conf.py` |
| مدیر فرایند | Supervisor (Redis + Gunicorn) | `deploy/supervisord.conf` |
| build/اجرا | Docker چندمرحله‌ای، کاربر غیرروت UID/GID 10001 | `Dockerfile` |
| سرو فایل‌های React | WhiteNoise (Django خودش SPA را سرو می‌کند) | `settings.py` (`WHITENOISE_ROOT`) |

زنجیرهٔ درخواست: `مرورگر → TLS در پراکسی دارکوب → HTTP به کانتینر :8000 → SecurityMiddleware → WhiteNoise/ReadinessMiddleware → CommonMiddleware → Django/DRF`.

نکتهٔ کلیدی معماری: فرانت‌اند و بک‌اند **یک سرویس و یک دامنه**اند؛ تمام مسیرهای غیر `/api/` توسط Django به `index.html` سرو می‌شوند و روتینگ صفحات در مرورگر (React Router) انجام می‌شود.

---

## ۲. بازبینی پیکربندی استقرار

- **Dockerfile** ([Dockerfile](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile)): مرحلهٔ build فرانت با Node 22، مرحلهٔ runtime با Python 3.12؛ نصب `redis-server` و `supervisor`؛ `USER 10001:10001`؛ `EXPOSE 8000`؛ `HEALTHCHECK` روی `deploy/healthcheck.py`؛ `ENTRYPOINT` روی `deploy/entrypoint.sh`. متغیرهای `REDIS_URL` و `UPLOADS_DIR` در image تعریف شده‌اند (L13-14).
- **entrypoint.sh** ([deploy/entrypoint.sh](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/entrypoint.sh)): `umask 027`، اجرای `prepare.py` و سپس `supervisord`. اگر آرگومان بدهی، دستور را مستقیم اجرا می‌کند (برای jobهای یک‌باره).
- **supervisord.conf** ([deploy/supervisord.conf](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/supervisord.conf)): `redis` (priority 10) و `web` = `gunicorn -c /app/backend/gunicorn.conf.py config.wsgi:application` (priority 20). لاگ روی stdout کانتینر.
- **gunicorn.conf.py** ([backend/gunicorn.conf.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py)): `bind 0.0.0.0:8000`، `workers=2`، `worker_class=gthread`، `threads=4`، `timeout=45`. **بدون** `worker_tmp_dir` و **بدون** تنظیمات control socket.
- **prepare.py** ([deploy/prepare.py](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/prepare.py)): قبل از بالا آمدن HTTP، بررسی قابل‌نوشتن بودن مسیرهای دیسک، اتصال PostgreSQL با retry، قفل advisory، `migrate`، `collectstatic`، `check`.
- **redis.conf** ([deploy/redis.conf](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/redis.conf)): فقط `127.0.0.1:6379`، `maxmemory 128mb`، `noeviction`.
- **healthcheck.py** ([deploy/healthcheck.py](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/healthcheck.py)): probe داخلی روی `http://127.0.0.1:8000/api/health/`.
- **سرو فایل ثابت**: WhiteNoise + `STATIC_ROOT`؛ SPA از `FRONTEND_ROOT`؛ فایل‌های خصوصی کاربران **فقط از API** (`/api/files/<id>/`) — به‌درستی عمومی نمی‌شوند.
- **متغیرهای محیطی مرتبط** (نمونه در [deploy/darkube.env.example](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/darkube.env.example) و [backend/.env.example](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/.env.example)): `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `REDIS_URL`, `UPLOADS_DIR`, `AVATARS_DIR`, `POSTS_DIR`, `SKILLS_DIR`, `TRUST_PROXY_PROTO`, `TRUSTED_PROXY_COUNT`.

---

## ۳. علت (علل) `ERR_TOO_MANY_REDIRECTS`

### مبنای منطقی
در [settings.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L72-L83):

- L72: `SECURE_SSL_REDIRECT = not DEBUG` → با `DEBUG=False` مقدار **True** است.
- L82-83: `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` **فقط اگر** `TRUST_PROXY_PROTO=True` باشد.
- L75: `SECURE_REDIRECT_EXEMPT = [r"^api/health/$"]` → فقط مسیر health از ریدایرکت مستثناست.
- L19-21: `SecurityMiddleware` **اولین** میدل‌ور است، پس ریدایرکت HTTPS روی همهٔ مسیرها (از جمله `/` و `/assets/...` و فاوآیکون) اعمال می‌شود.

منطق Django: اگر `request.is_secure()` نادرست باشد و `SECURE_SSL_REDIRECT=True`، پاسخ `301` به `https://...` داده می‌شود. `is_secure()` فقط وقتی True می‌شود که هدر اعلام‌شده در `SECURE_PROXY_SSL_HEADER` برابر مقدار `https` برسد.

### حلقهٔ ریدایرکت (فرضیهٔ قوی و علت اصلی)
1. مرورگر `https://okhovat.darkube.ir/` را می‌طلبد.
2. پراکسی دارکوب TLS را terminate و درخواست را به‌صورت **HTTP** به کانتینر `:8000` می‌فرستد.
3. اگر درخواست تحویلی به Django هدر معتبر `X-Forwarded-Proto: https` را نداشته باشد (یا اصلاً نباشد، یا مقدارش `http` باشد)، آنگاه `is_secure()==False`.
4. `SecurityMiddleware` پاسخ `301 → https://okhovat.darkube.ir/` می‌دهد.
5. پراکسی همان درخواست را مجدداً HTTP به Django می‌رساند → دوباره 301 → **حلقهٔ بی‌پایان** → `ERR_TOO_MANY_REDIRECTS`.

این فرضیه دو حالت دارد:
- **حالت A (محتمل‌تر):** مقدار `TRUST_PROXY_PROTO=True` **واقعاً در استقرار جاری اعمال نشده** (یا بعد از تغییر، deploy انجام نشده). چون در مخزن پیش‌فرض این گیت وجود دارد و نمونهٔ محیطی هم `False` است، اگر True نباشد `SECURE_PROXY_SSL_HEADER` ست نمی‌شود و Django همیشه http می‌بیند.
- **حالت B:** `TRUST_PROXY_PROTO=True` اعمال شده، اما پراکسی دارکوب هدر `X-Forwarded-Proto` را با مقدار `https` **بازنویسی نمی‌کند** (نمی‌فرستد یا `http` می‌فرستد). در این حالت هم حلقه ادامه دارد.

### شواهد تأییدکننده
- حلقه روی **فاوآیکون** هم رخ می‌دهد. فاوآیکون (`/assets/logo-ui.webp`، ارجاع در [index.html](file:///c:/Users/moham/Desktop/okhovat-react-django/frontend/index.html#L3)) توسط WhiteNoise سرو می‌شود، اما WhiteNoise **داخل** `SecurityMiddleware` است؛ پس ریدایرکت **قبل از** WhiteNoise و در لایهٔ Django رخ می‌دهد. این نشان می‌دهد منشأ حلقه فقط مسیرهای خاصی نیست، بلکه کل لایهٔ Django است.
- تست موجود در [test_deployment.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/test_deployment.py#L20-L22) صراحتاً رفتار مورد انتظار را تأیید می‌کند: روی `http://`، پاسخ `301` و `Location` با `https://` (یعنی این رفتار بخشی از طراحی is، نه باگ کد).

### تأیید وضعیت مخزن (طبق درخواست شما)
- `SECURE_SSL_REDIRECT` در مخزن **همچنان `not DEBUG`** است ([settings.py L72](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L72)). تغییر موقت `SECURE_SSL_REDIRECT = False` **در مخزن نیست** — یعنی یا اعمال نشده، یا فقط در محیط پنل بوده و commit/deploy نشده. بنابراین نمی‌توان به آن به‌عنوان عاملی مؤثر تکیه کرد.

### منابع ریدایرکت که **بررسی و رد شدند** (Confirmd: عامل نیستند)
- **Django custom middleware**: هیچ میدل‌وری ریدایرکت نمی‌کند. `SecurityHeaders` فقط هدر/محدودیت اضافه می‌کند ([security.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/security.py#L82-L114)) و `ReadinessMiddleware` فقط `/api/health/` را کوتاه می‌کند ([health.py L26-L36](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py#L26-L36)).
- **viewها**: هیچ `redirect()`/`HttpResponseRedirect` در `backend/` وجود ندارد (grep نتیجه‌ای نداشت).
- **فرانت‌اند**: هیچ ریدایرکت سمت سرور ندارد. `Navigate` در [main.tsx L35](file:///c:/Users/moham/Desktop/okhovat-react-django/frontend/src/main.tsx#L35) و `location.assign('/login/')` در [context.tsx L36](file:///c:/Users/moham/Desktop/okhovat-react-django/frontend/src/context.tsx#L36) صرفاً کلاینت‌ساید و پس از logout/گارد است.
- **APPEND_SLASH**: ست نشده (پیش‌فرض True) اما عملاً غیرفعال است؛ الگوی catch-all `re_path(r"^(?!api/).*", frontend)` در [urls.py L13-L16](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/urls.py#L13-L16) هر مسیر غیر `/api/` را می‌گیرد و ریدایرکت اسلش رخ نمی‌دهد.
- **PREPEND_WWW**: ست نشده (پیش‌فرض False). ریدایرکت canonical وجود ندارد.
- **Gunicorn/Supervisor/Redis**: هیچ‌کدام ریدایرکت HTTP انجام نمی‌دهند.

### آنچه **نامعلوم** است و به تأیید runtime نیاز دارد
- مقدار واقعی هدر ارسالی پراکسی دارکوب به بک‌اند (`X-Forwarded-Proto` یا هر نام دیگر مثل `X-Forwarded-Scheme` / `Front-End-Https`).
- اینکه آیا نسخهٔ مستقر واقعاً `TRUST_PROXY_PROTO=True` و `SECURE_SSL_REDIRECT` را همان‌طور که فکر می‌کنید دارد.
- اینکه آیا خود دارکوب ریدایرکت HTTP→HTTPS دارد یا نه.
- مقدار هدر `Host` که پراکسی به بک‌اند می‌فرستد (برای `ALLOWED_HOSTS`، و `USE_X_FORWARDED_HOST` که ست نشده و پیش‌فرض False است).

---

## ۴. سایر موانع/ریسک‌های استقرار

1. **`HOME` و سوکت کنترل Gunicorn (مشاهده‌شده).**
   - [Dockerfile L21](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile#L21) کاربر را با `--no-create-home` می‌سازد و در L10-14 هیچ `HOME` تعریف نشده است؛ بنابراین `HOME` از پلتفرم می‌آید (`/home/okhovat`) که وجود ندارد و قابل‌نوشتن نیست.
   - Gunicorn نسخهٔ 27.0.1 ([requirements.txt L13](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/requirements.txt#L13)) سوکت کنترل را زیر `HOME` می‌سازد → خطای `Permission denied: '/home/okhovat'`؛ با تغییر `HOME=/tmp` پیام `Control socket listening at /tmp/.gunicorn/gunicorn.ctl` ظاهر شده.
   - **این عاملِ حلقهٔ ریدایرکت نیست**، اما یک وابستگی محیطی شکننده است که باید پایدار شود.

2. **`TRUSTED_PROXY_COUNT=0` پشت پراکسی.** شمارش نرخ ورود بر اساس IP پروکسی مشترک می‌شود ([security.py check_login_rate](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/security.py#L48-L64)). ریسک UX/امنیتی است، نه ریدایرکت.

3. **HSTS یک‌ساله با include_subdomains** ([settings.py L76-L78](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L76-L78)). به‌محض اولین پاسخ صحیح HTTPS، مرورگر برای یک سال HTTPS را اجباری می‌کند؛ در دیباگ محدودکننده است (preload خاموش است، خوب).

4. **`USE_X_FORWARDED_HOST` ست نشده** (پیش‌فرض False). اگر Host تحویلی متفاوت باشد، به‌جای ریدایرکت، خطای `DisallowedHost (400)` می‌گیرید. (فقط `/api/health/` از کنترل Host معاف است.)

5. **هم‌خوانی مستندات و کد.** [docs/DARKUBE.md L61](file:///c:/Users/moham/Desktop/okhovat-react-django/docs/DARKUBE.md#L61) صراحتاً همین سناریو را هشدار داده: «اگر HTTPS در پراکسی terminate شود ولی این گزینه خاموش بماند، ممکن است redirect loop ببینی؛ روش صحیح تنظیم پراکسی است، نه خاموش‌کردن امنیت سایت.»

---

## ۵. ریسک‌های امنیتی (بدون تضعیف امنیت باید بمانند)

- **رفتار خوب و باید حفظ شود:** `SECURE_SSL_REDIRECT=True`، کوکی‌های Secure/HttpOnly/SameSite ([settings.py L67-L71](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L67-L71))، HSTS، CSP و X-Frame-Options و nosniff ([security.py L96-L105](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/security.py#L96-L105))، اعتبارسنجی و بازنویسی تصویر آپلودی ([views.py L380-L398](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/views.py#L380-L398))، Argon2 برای رمز، بررسی طول/یکتایی `SECRET_KEY` ([settings.py L9-L10](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L9-L10)).
- **ریسک ثانویهٔ حلقه:** راه‌حل «خاموش‌کردن `SECURE_SSL_REDIRECT`» اگر بدون تضمین سمت پراکسی انجام شود، امکان downgrade به HTTP می‌دهد. اگر انتخاب شد، فقط در صورتی امن است که **پراکسی دارکوب قطعاً HTTP→HTTPS را اجبار کند**.
- **`TRUST_PROXY_PROTO`**: فقط با پراکسی‌ای که هدر را **خودش بازنویسی** می‌کند باید True باشد؛ در غیر این‌صورت مهاجم می‌تواند هدر جعلی بفرستد.
- **`TRUSTED_PROXY_COUNT`**: بدون بازنویسی `X-Forwarded-For` توسط پراکسی، نباید > 0 شود.
- هیچ فایل `.env` در مخزن/ایمیج نیست (طبق [.dockerignore L10-L12](file:///c:/Users/moham/Desktop/okhovat-react-django/.dockerignore#L10-L12)) — خوب.

---

## ۶. اصلاحات پیشنهادی، به‌ترتیب اولویت

### P0 — رفع حلقهٔ ریدایرکت (اصلی‌ترین هدف)
تشخیص دقیق و سپس یکی از دو مسیر:
- **مسیر ۱ (ترجیح‌داده‌شده، حفظ امنیت در لایهٔ اپ):** تعیین هدر واقعی پراکسی دارکوب و تنظیم `SECURE_PROXY_SSL_HEADER` مطابق آن، با `TRUST_PROXY_PROTO=True` و **اطمینان از deploy شدن**.
  - اگر دارکوب `X-Forwarded-Proto: https` می‌فرستد → کد فعلی کافی است؛ فقط True+deploy لازم است.
  - اگر نام هدر متفاوت است (مثل `X-Forwarded-Scheme`) → باید `SECURE_PROXY_SSL_HEADER` در [settings.py L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83) به همان هدر تغییر کند.
- **مسیر ۲ (در صورت عدم‌ارسال هدر توسط دارکوب):** اجبار HTTPS در پراکسی و خاموش‌کردن ریدایرکت در اپ (`SECURE_SSL_REDIRECT=False`). فقط با تضمین سمت پراکسی امن است و defense-in-depth را حذف می‌کند.

### P1 — پایداری `HOME`/سوکت Gunicorn
- افزودن `ENV HOME=/tmp` به [Dockerfile](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile#L10-L14)، و/یا افزودن `worker_tmp_dir = "/tmp"` به [gunicorn.conf.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py).
- سطح Erfolg: بدون وابستگی به متغیر پلتفرم، دیگر خطای `Permission denied` روی `HOME` رخ ندهد.

### P2 — `TRUSTED_PROXY_COUNT`
- پس از تأیید بازنویسی `X-Forwarded-For` توسط پراکسی، مقدار `1`.

### P3 — تأیید نهایی امنیت
- `python manage.py check --deploy` روی محیط واقعی و بازبینی هدرهای پاسخ.

---

## ۷. فایل‌ها و متغیرهایی که احتمالاً باید تغییر کنند

| مورد | فایل/متغیر | نوع تغییر |
|---|---|---|
| منشأ حلقه | `TRUST_PROXY_PROTO` (متغیر محیطی) | True + اطمینان از deploy (بدون تغییر کد اگر دارکوب هدر استاندارد بفرستد) |
| هدر غیراستاندارد | `backend/config/settings.py` L82-83 | تغییر `SECURE_PROXY_SSL_HEADER` به هدر واقعی دارکوب (فقط در صورت نیاز) |
| جایگزین | `SECURE_SSL_REDIRECT` (در settings) | فقط اگر راه‌حل پراکسی‌محور انتخاب شود |
| HOME | `Dockerfile` (L10-14) و/یا `backend/gunicorn.conf.py` | افزودن `HOME=/tmp` و/یا `worker_tmp_dir` |
| IP واقعی | `TRUSTED_PROXY_COUNT` | `1` پس از تأیید |

---

## ۸. تفکیک قطعیت یافته‌ها

- **باگ‌های تأییدشده (Confirmed):**
  - `SECURE_SSL_REDIRECT=True` در استقرار (به‌دلیل `DEBUG=False`).
  - هیچ منبع ریدایرکتی جز `SecurityMiddleware` در کد نیست.
  - `HOME` در ایمیج تعریف نشده و کاربر بدون home ساخته می‌شود → سوکت کنترل Gunicorn به HOME وابسته است.
- **فرضیه‌های قوی (Strong hypotheses):**
  - حلقه ناشی از عدم‌تطابق پروتکل تحویلی به Django (نبود/نادرستی `X-Forwarded-Proto`) یا عدم‌اعمال واقعی `TRUST_PROXY_PROTO=True`.
- **نامعلوم‌های زیرساخت (Unknown):**
  - هدر واقعی پراکسی دارکوب؛ داشتن/نداشتن ریدایرکت HTTP→HTTPS در پراکسی؛ مقدار Host تحویلی.
- **توصیه‌ها (Recommendations):** موارد P1–P3 بالا.

---

## ۹. برنامهٔ امن دیباگ و استقرار (گام‌به‌گام، بدون تغییر مخرب)

توجه: هیچ‌کدام از گام‌ها migration اجرا نمی‌کند، فایل حذف نمی‌کند یا امنیت را تضعیف نمی‌کند. دستور `curl` فقط خواندنی است.

1. **تثبیت تصویر فعلی:** SHA دقیق commit مستقر و لیست متغیرهای محیطی فعال را از پنل دارکوب یادداشت کن (خصوصاً `DEBUG`, `TRUST_PROXY_PROTO`, `TRUSTED_PROXY_COUNT`, `ALLOWED_HOSTS`).
2. **probe درون‌کانتینری (شاهد حلقه):**
   ```sh
   curl -sSI -H 'Host: okhovat.darkube.ir' http://127.0.0.1:8000/
   ```
   انتظار: `301` و `Location: https://okhovat.darkube.ir/` (اثبات فعال بودن ریدایرکت).
3. **شبیه‌سازی هدر پراکسی (شاهد منطق هدر):**
   ```sh
   curl -sSI -H 'Host: okhovat.darkube.ir' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/
   ```
   انتظار: `200` (اثبات اینکه با هدر درست، حلقه رخ نمی‌دهد).
4. **probe از بیرون (منشأ زنجیره):**
   ```sh
   curl -sSI https://okhovat.darkube.ir/
   curl -sSI http://okhovat.darkube.ir/
   ```
   پاسخ‌ها را از نظر `Server`، تعداد `301/302` و مقصد `Location` مقایسه کن تا معلوم شود ریدایرکت از پراکسی است یا از Django.
5. **تعیین رفتار پراکسی دارکوب:** از مستندات/پشتیبانی بگیر که چه هدری (proto) به بک‌اند می‌رسد؛ یا با افزودن یک لاگ موقت فقط-خواندنی از `request.META.get("HTTP_X_FORWARDED_PROTO")` در `/api/health/` (بدون افشای داده) این مقدار را در لاگ ببین.
6. **اعمال اصلاح P0:** مطابق مسیر ۱ یا ۲ بالا تنظیم کن و **deploy کن**.
7. **گام‌های P1 (HOME):** `HOME=/tmp` در Dockerfile و/یا `worker_tmp_dir=/tmp` در Gunicorn.
8. **اعتبارسنجی:** تکرار گام‌های 2–4؛ انتظار: `/` و فاوآیکون بدون حلقه، `Location` درست، هدرهای HSTS/CSP/Cookies موجود.
9. **گام‌های P2/P3:** `TRUSTED_PROXY_COUNT=1` پس از تأیید پراکسی، و `python manage.py check --deploy`.

**معیار پذیرش:** `curl -I https://okhovat.darkube.ir/` حداکثر یک ریدایرکت (یا صفر) داشته باشد و به `200` با صفحهٔ SPA برسد؛ و `SECURE_SSL_REDIRECT`/کوکی‌های امن در محیط باقی بمانند.

---

## ۱۰. جمع‌بندی یک‌خطی
حلقهٔ ریدایرکت با احتمال بالا محصول `SECURE_SSL_REDIRECT=True` همراه با نرسیدن هدر معتبر `X-Forwarded-Proto: https` از پراکسی دارکوب به Django است؛ اصلاح صحیح، **راستی‌آزمایی و تنظیم درست اعتماد به پراکسی** است (نه خاموش‌کردن امنیت)، به‌همراه پایدارسازی `HOME` برای Gunicorn.
