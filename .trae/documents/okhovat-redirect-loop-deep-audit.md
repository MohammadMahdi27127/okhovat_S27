# ممیزی عمیق — بررسی ریشه‌ای حلقهٔ ریدایرکت (ERR_TOO_MANY_REDIRECTS)

**دامنهٔ تولید:** `https://okhovat.darkube.ir`
**وضعیت:** فقط-بررسی. هیچ فایل، متغیر محیطی یا کانفیگ تغییری نکرده است.
**مبنای گزارش:** بازخوانی مستقیم مخزن (بدون تکیه بر نتیجه‌گیری‌های قبلی).

---

## ۱. تأیید وضعیت واقعی مخزن (کد و شمارهٔ خط)

### ۱.۱ `backend/config/settings.py`
| مورد | خط | مقدار واقعی |
|---|---|---|
| `DEBUG` | L7 | `env("DEBUG")` (در تولید `False`) |
| `SECURE_SSL_REDIRECT` | **L72** | **`= not DEBUG`** → در تولید **`True`** |
| `SECURE_REDIRECT_EXEMPT` | L75 | `[r"^api/health/$"]` |
| `SECURE_HSTS_SECONDS` | L76 | `31536000 if not DEBUG else 0` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | L77 | `True` |
| `SECURE_HSTS_PRELOAD` | L78 | `False` |
| `SECURE_PROXY_SSL_HEADER` | **L82-83** | فقط اگر `TRUST_PROXY_PROTO=True` → `("HTTP_X_FORWARDED_PROTO","https")` |
| `TRUSTED_PROXY_COUNT` | L84-86 | `env.int(..., default=0)`، اعتبارسنجی ۰..۳ |
| `SESSION_COOKIE_SECURE` | L69 | `not DEBUG` → `True` |
| `CSRF_COOKIE_SECURE` | L70 | `not DEBUG` → `True` |
| `ALLOWED_HOSTS` | L11 | از env؛ در تولید اجباری و بدون `*` |
| `CSRF_TRUSTED_ORIGINS` | L14 | از env |
| `MIDDLEWARE` | L19-29 | به ترتیب: `SecurityMiddleware` → `WhiteNoiseMiddleware` → `core.security.SecurityHeaders` → `core.health.ReadinessMiddleware` → `SessionMiddleware` → `CommonMiddleware` → `XFrameOptionsMiddleware` → `CsrfViewMiddleware` → `AuthenticationMiddleware` |
| `USE_X_FORWARDED_HOST` | — | **تعریف نشده** (پیش‌فرض Django = `False`) |
| `APPEND_SLASH` | — | **تعریف نشده** (پیش‌فرض Django = `True`) |
| `PREPEND_WWW` | — | **تعریف نشده** (پیش‌فرض Django = `False`) |

**نتیجهٔ صریح:** مقدار فعلی `SECURE_SSL_REDIRECT` در مخزن **`not DEBUG`** است، یعنی در تولید **`True`**. عبارت `SECURE_SSL_REDIRECT = False` که به‌عنوان «تغییر موقت» ذکر شده، **در `backend/config/settings.py` وجود ندارد**.

### ۱.۲ محل واقعی `SECURE_SSL_REDIRECT = False` در مخزن
تنها دو فایل، مقدار `False` را ست می‌کنند و هر دو **فقط برای تست** هستند:
- [config/test_settings.py L12](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/test_settings.py#L12) (SQLite/حافظه‌ای، `os.environ["DEBUG"]="True"` در L7).
- [config/integration_test_settings.py L10](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/integration_test_settings.py#L10) (نیازمند `TEST_REDIS_URL`، صراحتاً «never production»).

این‌ها `config.settings` را `import *` می‌کنند و بعد بازنویسی می‌کنند؛ در تولید استفاده **نمی‌شوند**، چون:
- [config/wsgi.py L3](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/wsgi.py#L3) مقدار پیش‌فرض `DJANGO_SETTINGS_MODULE` را `config.settings` تعیین می‌کند،
- و [supervisord.conf L26](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/supervisord.conf#L26) Gunicorn را با `config.wsgi:application` اجرا می‌کند.

> اگر کسی «تغییر موقت» را در `test_settings.py` یا `integration_test_settings.py` گذاشته باشد، **هیچ اثری روی تولید ندارد** (فرضیهٔ H1). این نکته باید در مرحلهٔ تشخیص بررسی شود.

### ۱.۳ بقیهٔ فایل‌های استقرار (خطوط کلیدی)
- **Dockerfile** ([Dockerfile](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile)): L9-14 runtime، `ENV REDIS_URL`/`UPLOADS_DIR` — **بدون `ENV HOME`**؛ L21 `useradd ... --no-create-home`؛ L34 `USER 10001:10001`؛ L35 `EXPOSE 8000`؛ L37-38 HEALTHCHECK؛ L39 ENTRYPOINT. هیچ دستور سرورِ TLS ندارد (کانتینر فقط HTTP سرو می‌کند).
- **deploy/entrypoint.sh** ([entrypoint.sh](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/entrypoint.sh)): L1-9؛ L11 `prepare.py`؛ L12 `supervisord`.
- **deploy/supervisord.conf** ([supervisord.conf](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/supervisord.conf)): L9-23 redis؛ L25-38 web = `gunicorn -c /app/backend/gunicorn.conf.py config.wsgi:application`.
- **backend/gunicorn.conf.py** ([gunicorn.conf.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py)): L1 `bind="0.0.0.0:8000"`، L2 `workers=2`، L3 `worker_class="gthread"`، L4 `threads=4`. **بدون** TLS، **بدون** `worker_tmp_dir`، **بدون** تنظیمات سوکت کنترل.
- **backend/config/urls.py** ([urls.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/urls.py)): L5-11 view `frontend` (سرو `index.html` با `FileResponse`، بدون ریدایرکت)؛ L14 `api/`؛ **L15 catch-all** `re_path(r"^(?!api/).*", frontend)`.
- **backend/core/security.py** ([security.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/security.py)): `SecurityHeaders` L82-114 — فقط هدر اضافه/محدودیت اندازه؛ **هیچ تغییری در `request.META` یا `scheme`** و **هیچ ریدایرکتی** ندارد. `check_login_rate` L48-64 فقط نرخ ورود.
- **backend/core/health.py** ([health.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py)): `readiness` L11-23 (پاسخ JSON، بدون ریدایرکت)؛ `ReadinessMiddleware` L26-36 فقط مسیر دقیق `/api/health/` را کوتاه می‌کند.
- **backend/core/views.py** ([views.py L30](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/views.py#L30)): `from .health import readiness as health` → مسیر `/api/health/` در urls همان readiness است.
- **frontend** روتینگ: [main.tsx L110-119](file:///c:/Users/moham/Desktop/okhovat-react-django/frontend/src/main.tsx#L110-L119) `BrowserRouter`/`Routes` (کلاینت‌ساید). نسخهٔ react-router-dom `^7.9.0` ([package.json L17](file:///c:/Users/moham/Desktop/okhovat-react-django/frontend/package.json#L17)).

---

## ۲. مسیر تشخیص HTTPS در Django (تحلیل دقیق)

### ۲.۱ `request.is_secure()` چگونه تعیین می‌شود
- `request.is_secure()` معادل `request.scheme == "https"` است.
- `request.scheme` در `WSGIRequest` بر پایهٔ `wsgi.url_scheme` و **در صورت وجود** `SECURE_PROXY_SSL_HEADER` محاسبه می‌شود.
- `SECURE_PROXY_SSL_HEADER` یک جفت `(HEADER, value)` است؛ اگر مقدار `request.META[HEADER] == value` باشد، آنگاه `scheme == "https"`.
- کلید `META` شکل نرمال‌شدهٔ WSGI است: حروف بزرگ، خط تیره→زیرخط، پیشوند `HTTP_`. بنابراین هدر HTTP `X-Forwarded-Proto` در `request.META` با کلید `HTTP_X_FORWARDED_PROTO` دیده می‌شود.

### ۲.۲ هدری که این اپ می‌خواند
[settings.py L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83):
```python
if env.bool("TRUST_PROXY_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```
- هدر: `X-Forwarded-Proto` (در `META`: `HTTP_X_FORWARDED_PROTO`)، مقدار مورد انتظار: **دقیقاً** `https`.
- **شرط فعال‌بودن:** `TRUST_PROXY_PROTO=True`. اگر این متغیر `False` یا غایب باشد، `SECURE_PROXY_SSL_HEADER` **تعریف نمی‌شود** و Django هرگز `https` تشخیص نمی‌دهد.

### ۲.۳ آیا هدر/مقدار با رفتار واقعی پراکسی منطبق است؟
- **از کد قابل تعیین نیست.** اینکه پراکسی دارکوب دقیقاً `X-Forwarded-Proto: https` می‌فرستد یا نه، در مخزن مشخص نیست و **نیازمند تأیید runtime** است.
- نکتهٔ حساس: تطبیق **برابری دقیق** است. اگر پراکسی مقدار ترکیبی مثل `https, http` (زنجیره) بفرستد، تطبیق **شکست می‌خورد** و Django هم `http` می‌بیند.

### ۲.۴ آیا میدل‌وری `request.META`/`scheme` را تغییر می‌دهد؟
- **خیر.** `SecurityHeaders` ([security.py L82-114](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/security.py#L82-L114)) و `ReadinessMiddleware` ([health.py L26-36](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py#L26-L36)) هیچ‌کدام `request.META`، `wsgi.url_scheme` یا `_scheme` را دستکاری نمی‌کنند. هیچ میدل‌ور سفارشی دیگری وجود ندارد ([apps.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/apps.py) فقط `signals` را import می‌کند؛ [signals.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/signals.py) فقط کش را باطل می‌کند).

### ۲.۵ اثر `USE_X_FORWARDED_HOST`
- تعریف نشده → `False`. این تنها روی **تشخیص `Host`** اثر دارد (اگر فعال باشد، به `X-Forwarded-Host` اعتماد می‌کند)، **نه روی scheme/HTTPS**. بنابراین علت حلقه نیست؛ اما اگر پراکسی `Host` غیرمنتظره‌ای بفرستد، به‌جای ریدایرکت احتمالاً `DisallowedHost (400)` می‌گیریم (به‌جز `/api/health/` که از کنترل Host معاف است).

### ۲.۶ Gunicorn و پروتکلی که Django می‌بیند
- [gunicorn.conf.py L1](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py#L1) فقط `bind="0.0.0.0:8000"` است؛ هیچ TLS/`ssl_*` وجود ندارد. پس `wsgi.url_scheme` همیشه **`http`** است.
- نتیجه: بدون هدر معتبر پراکسی، `is_secure()` **همیشه `False`** است.

### ۲.۷ تمام مسیرهایی که می‌توانند ریدایرکت HTTPS در Django بسازند
1. **`SecurityMiddleware` + `SECURE_SSL_REDIRECT=True` + `is_secure()==False` + مسیر غیرمستثنا** → `301` به `https://<host><path>`. **این تنها مسیر فعال در این پروژه است.**
2. `CommonMiddleware` + `APPEND_SLASH` (پیش‌فرض True): می‌تواند `301` اضافه‌کردن اسلش بدهد — **در عمل بی‌اثر**، چون الگوی catch-all ([urls.py L15](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/urls.py#L15)) هر مسیر غیر `/api/` را می‌گیرد و `is_valid_path` را موفق می‌کند.
3. `CommonMiddleware` + `PREPEND_WWW=True` → ریدایرکت به `www.` — **غیرفعال** (تعریف نشده).

---

## ۳. جست‌وجوی همهٔ منابع ریدایرکت

جست‌وجو روی کل مخزن برای: `redirect(`, `HttpResponseRedirect`, `HttpResponsePermanentRedirect`, `SECURE_SSL_REDIRECT`, `APPEND_SLASH`, `PREPEND_WWW`, `window.location`, `Navigate`, `navigate(`, canonical, auth redirects, middleware redirects.

| فایل | خط | شرط ریدایرکت | مقصد | می‌تواند حلقهٔ فعلی را بسازد؟ |
|---|---|---|---|---|
| `backend/config/settings.py` | 72 | `SECURE_SSL_REDIRECT = not DEBUG` (فعال در تولید) | — (فعال‌ساز) | **بله — عامل اصلی** (از طریق SecurityMiddleware) |
| `backend/config/settings.py` | 75 | `SECURE_REDIRECT_EXEMPT` فقط `^api/health/$` | — | نه (فقط health را معاف می‌کند؛ بقیه را معاف نمی‌کند) |
| (framework) `django.middleware.security.SecurityMiddleware` | — | `SECURE_SSL_REDIRECT` و `not is_secure()` و مسیر غیرمستثنا | `https://<host><path>` (301) | **بله — مسیر واقعی حلقه** |
| (framework) `django.middleware.common.CommonMiddleware` | — | `APPEND_SLASH` و مسیر بدون اسلش | `.../` (301) | نه (catch-all آن را بی‌اثر می‌کند) |
| (framework) `CommonMiddleware` | — | `PREPEND_WWW=True` | `www.` | نه (غیرفعال) |
| `backend/core/security.py` | 82-114 | — | — | نه (فقط هدر/محدودیت؛ بدون ریدایرکت) |
| `backend/core/health.py` | 26-36 | `path_info == "/api/health/"` | پاسخ مستقیم (200/503) | نه |
| `backend/config/urls.py` | 5-15 | catch-all غیر `/api/` | `index.html` (200) | نه |
| `backend/core/views.py` | کل فایل | — | — | نه (هیچ `redirect`/`HttpResponseRedirect` وجود ندارد) |
| `frontend/src/main.tsx` | 35 | `!user` در `Guard` | `/login/?next=...` | نه (کلاینت‌ساید؛ روی `/` بدون گارد) |
| `frontend/src/main.tsx` | 87 | خطای اپ → `window.location.reload()` | همان URL | نه (reload، نه ریدایرکت) |
| `frontend/src/context.tsx` | 36 | پس از `logout` | `/login/` | نه (فقط پس از خروج) |
| `frontend/src/pages/Auth.tsx` | 17 | پس از ورود موفق | `next` یا `/` | نه |
| `frontend/src/pages/NewPost.tsx` | 18 | پس از انتشار پست | `/posts/` | نه |
| `backend/config/test_settings.py` | 12 | تست | — | نه (فقط تست) |
| `backend/config/integration_test_settings.py` | 10 | تست | — | نه (فقط تست) |
| `backend/core/test_deployment.py` | 13, 20-22 | تست انتظار `301` روی `http://` | `https://` | نه (تست است، ولی رفتار واقعی را تأیید می‌کند) |

**جمع‌بندی:** تنها منبع ریدایرکت مؤثر روی `/` در این کد، `SecurityMiddleware` است. هیچ منبع ریدایرکت دیگری — سرورساید یا کلاینت‌ساید — روی `/` اثر ندارد.

---

## ۴. پراکسی معکوس دارکوب: چه می‌دانیم و چه نمی‌دانیم

### ۴.۱ آنچه از مخزن قطعی است (Known)
- کانتینر فقط **HTTP** روی `0.0.0.0:8000` سرو می‌کند ([gunicorn.conf.py L1](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py#L1))؛ بنابراین هر TLS باید در پراکسی terminate شود.
- اپ فقط وقتی `https` را باور می‌کند که هدر `X-Forwarded-Proto: https` برسد **و** `TRUST_PROXY_PROTO=True` باشد ([settings.py L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83)).
- `TRUSTED_PROXY_COUNT` فقط روی تشخیص IP (DRF `NUM_PROXIES`) اثر دارد، نه روی scheme.
- تنها مسیر معاف از HTTPS و کنترل Host: `/api/health/` ([settings.py L75](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L75)، [health.py L34](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py#L34)).
- مستندات پروژه خودش همین سناریو را هشدار داده: [docs/DARKUBE.md L61](file:///c:/Users/moham/Desktop/okhovat-react-django/docs/DARKUBE.md#L61).

### ۴.۲ آنچه **از کد قابل تعیین نیست** (Unknown — نیازمند تأیید runtime)
1. آیا درخواست ورودی به Gunicorn با HTTP می‌رسد یا HTTPS؟ (از کانفیگ فقط HTTP محتمل است، ولی پراکسی چه می‌فرستد؟)
2. آیا پراکسی هدر `X-Forwarded-Proto` را می‌فرستد؟
3. مقدار دقیق آن چیست؟ (`https`، `http`، یا ترکیبی مثل `https, http`؟)
4. آیا پراکسی هدر را **بازنویسی (replace)** می‌کند یا **به زنجیره اضافه (append)** می‌کند؟ (تفاوت حیاتی: append می‌تواند باعث عدم تطابق برابری شود و همچنین ریسک جعل هدر دارد.)
5. آیا لایهٔ دیگری (CDN/LB) در زنجیره هست که hop اضافه کند؟
6. آیا خود دارکوب ریدایرکت HTTP→HTTPS انجام می‌دهد؟
7. مقدار `Host` که پراکسی به بک‌اند می‌فرستد چیست؟

> **تأکید:** تنظیم `TRUSTED_PROXY_COUNT=1` **بدون شاهد** توصیه نمی‌شود. همچنین نباید نام هدر پراکسی را حدس زد؛ باید از پراکسی/مستندات دارکوب راستی‌آزمایی شود.

---

## ۵. تحلیل آخرین لاگ‌های استقرار

**مشاهدات:** migrationها کامل، system check پاس، Redis بالا، Gunicorn روی `0.0.0.0:8000`، دو worker بالا، سوکت کنترل Gunicorn زیر `/tmp/.gunicorn/gunicorn.ctl`، و خطای `Permission denied: '/home/okhovat'` دیگر نیست.

### چه چیزی **اثبات** می‌شود
- `prepare.py` با موفقیت اجرا شده: مسیرهای `/data/avatars|posts|skills` و `/srv/okhovat/private-media` قابل‌نوشتن‌اند ([prepare.py L26-35](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/prepare.py#L26-L35)).
- PostgreSQL در دسترس بوده و `migrate` + `collectstatic` + `check` اجرا شده ([prepare.py L37-68](file:///c:/Users/moham/Desktop/okhovat-react-django/deploy/prepare.py#L37-L68)).
- Supervisor هر دو فرایند را بالا آورده و Gunicorn روی پورت ۸۰۰۰ listen می‌کند.
- مشکل `HOME` مقدماتی حل شده: سوکت کنترل الان زیر `/tmp` است (یعنی `HOME` در زمان اجرا به مسیر قابل‌نوشتن تغییر کرده)، ولی این تغییر **در `Dockerfile` ثبت نشده** ([Dockerfile L10-14](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile#L10-L14) بدون `ENV HOME`) و به تنظیمات پلتفرم وابسته است.

### چه چیزی **اثبات نمی‌شود**
- موفقیت درخواست‌های واقعی (HTTP 200) — **لاگ استارتاپ، لاگ درخواست نیست**.
- اینکه `TRUST_PROXY_PROTO` واقعاً اعمال شده یا هدر پراکسی می‌رسد.
- اینکه نسخهٔ در حال اجرا واقعاً `SECURE_SSL_REDIRECT=False` دارد (طبق بند ۱ در مخزن `True` است).
- اینکه درخواست هرگز به لایهٔ view می‌رسد.

> **نکتهٔ منطقی کلیدی:** `HEALTHCHECK`/readiness روی `/api/health/` اجرا می‌شود که **از ریدایرکت HTTPS معاف** است ([settings.py L75](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L75)، [health.py L34](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py#L34)) و با IP پاد کار می‌کند. پس **کاملاً سازگار است** که سرویس RUNNING و readiness سالم باشد، درحالی‌که همهٔ مسیرهای عمومی (از جمله `/` و فاوآیکون) در حلقهٔ ریدایرکت باشند. یعنی «سبز بودن readiness» حلقه را رد نمی‌کند.

---

## ۶. تحلیل «تست ناموفق HTTPS» (SECURE_SSL_REDIRECT=False)

فرضیه‌ها به‌ترتیب احتمال:

| رتبه | فرضیه | چرا محتمل است | چگونه تأیید کنیم |
|---|---|---|---|
| **H1** | تغییر موقت **واقعاً deploy نشده** (یا در فایل تست گذاشته شده) | مخزن همچنان `not DEBUG` دارد ([settings.py L72](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L72))؛ و `=False` فقط در فایل‌های تست است که در تولید استفاده نمی‌شوند | خواندن مقدار مؤثر در ایمیج در حال اجرا با `python -c ...` (بخش ۷) + بررسی commit مستقر |
| **H2** | منبع حلقه **خود پراکسی دارکوب** است (ریدایرکت/کانونیکال مستقل) | اگر پراکسی مستقل ریدایرکت کند، خاموش‌کردن تنظیم Django هیچ اثری ندارد | `curl.exe -I http://...` و `https://...`؛ بررسی هدر `Server`/`Location`؛ مقایسهٔ پاسخ پراکسی با پاسخ مستقیم کانتینر |
| **H3** | **کش مرورگر و/یا HSTS** رفتار قدیمی را تثبیت کرده | `301` دائمی کش می‌شود؛ `SECURE_HSTS_SECONDS=31536000` ([settings.py L76](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L76)) به‌مدت یک سال HTTPS را اجباری می‌کند | تست در پنجرهٔ ناشناس/مرورگر دیگر + `curl.exe` (بدون کش)؛ پاک‌کردن HSTS از `chrome://net-internals/#hsts` |
| **H4** | منبع ریدایرکت دیگر در اپ (میدل‌ور/view) | **بعید** — جست‌وجو منبعی نیافت | جدول بخش ۳ |
| **H5** | میدل‌ور کانفیگ دیگر (مثل `APPEND_SLASH`) | **بعید** — catch-all آن را بی‌اثر می‌کند | جدول بخش ۳ |

**تأکید:** H1 و H2 هم‌زمان می‌توانند درست باشند (هر دو مستقل از هم حلقه می‌سازند). تشخیص باید هر دو را جدا آزمون کند.

---

## ۷. برنامهٔ تشخیص شواهد‌محور (فقط-خواندنی)

> همهٔ دستورها **خواندنی**اند: هیچ migration، حذف فایل، تغییر DB یا تغییر کانفیگ انجام نمی‌دهند. روی Windows PowerShell از `curl.exe` استفاده کنید (نه alias `curl`).

### الف) از ماشین خودتان (بررسی زنجیرهٔ عمومی)
```powershell
# ۱) هدرهای پاسخ ریشه روی HTTPS (بدون دنبال‌کردن ریدایرکت)
curl.exe -sS -I https://okhovat.darkube.ir/

# ۲) زنجیرهٔ کامل ریدایرکت + شمارش
curl.exe -sS -L -o NUL -w "num_redirects=%{num_redirects} final=%{url_effective} code=%{http_code}`n" https://okhovat.darkube.ir/

# ۳) رفتار روی HTTP خام
curl.exe -sS -I http://okhovat.darkube.ir/

# ۴) فاوآیکون (همان مسیری که در مرورگر حلقه دارد)
curl.exe -sS -I https://okhovat.darkube.ir/assets/logo-ui.webp

# ۵) health روی HTTPS و HTTP
curl.exe -sS -i https://okhovat.darkube.ir/api/health/
curl.exe -sS -i http://okhovat.darkube.ir/api/health/

# ۶) جزئیات دقیق: منشأ (Server) و مقصد (Location) و HSTS
curl.exe -sS -v https://okhovat.darkube.ir/ 2>&1 | Select-String -Pattern "HTTP/|location:|server:|strict-transport-security"
```
**هر دستور چه چیزی را اثبات می‌کند**
- ۱: آیا روی HTTPS پاسخ `200` است یا `301/302`؟ اگر `301` بدهد، حلقه در لایهٔ پراکسی تأیید می‌شود.
- ۲: اگر `num_redirects` به سقف (معمولاً ۲۰) برسد و `code=000/301`، حلقه تأیید می‌شود؛ `final` نشان می‌دهد مقصد تکرارشونده است.
- ۳ و ۵: آیا پراکسی HTTP را به HTTPS ریدایرکت می‌کند (رفتار پراکسی) و آیا `/api/health/` روی HTTP معاف است (`200 {"ok": true}`).
- ۴: تأیید می‌کند فاوآیکون هم مثل ریشه گرفتار است (منشأ مشترک = لایهٔ Django یا پراکسی).
- ۶: `server:` (نام پراکسی/سرور) و الگوی `location:` (همان دامنه با https ← نشانهٔ حلقه در لایهٔ ریدایرکت) و وجود `Strict-Transport-Security` (اثر HSTS).

### ب) از ترمینال کانتینر در پنل دارکوب (بررسی لایهٔ اپ — قطعی‌ترین شواهد)
```sh
# ۱) ریدایرکت اپ بدون هدر پراکسی را ببینید
curl -sSI -H 'Host: okhovat.darkube.ir' http://127.0.0.1:8000/

# ۲) همان درخواست با هدر پروتو (باید 200 شود = سیم‌کشی درست)
curl -sSI -H 'Host: okhovat.darkube.ir' -H 'X-Forwarded-Proto: https' http://127.0.0.1:8000/

# ۳) مقدار مؤثر تنظیمات در ایمیج در حال اجرا (خواندنی و قطعی)
cd /app/backend
python -c "import os,django;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');django.setup();
from django.conf import settings as s;
print('SECURE_SSL_REDIRECT=', s.SECURE_SSL_REDIRECT);
print('SECURE_PROXY_SSL_HEADER=', getattr(s,'SECURE_PROXY_SSL_HEADER',None));
print('SECURE_REDIRECT_EXEMPT=', s.SECURE_REDIRECT_EXEMPT);
print('ALLOWED_HOSTS=', s.ALLOWED_HOSTS);
print('USE_X_FORWARDED_HOST=', s.USE_X_FORWARDED_HOST)"

# ۴) بررسی امنیتی غیرتخریبی
python manage.py check --deploy
```
**هر دستور چه چیزی را اثبات می‌کند**
- ۱: تأیید می‌کند `SecurityMiddleware` فعلاً `301` می‌دهد (یعنی اپ منابع ریدایرکت را فعال دارد).
- ۲: تأیید می‌کند با هدر درست، ریدایرکت رخ نمی‌دهد (سیم‌کشی `TRUST_PROXY_PROTO` + not-https detection).
- **۳ (مهم‌ترین):** مقدار واقعی `SECURE_SSL_REDIRECT` و `SECURE_PROXY_SSL_HEADER` در نسخهٔ مستقر را نشان می‌دهد؛ فرضیهٔ H1 را قطعی می‌کند.
- ۴: فقط هشدارهای پیکربندی (W0xx) را چاپ می‌کند؛ چیزی تغییر نمی‌دهد.

> برای تشخیص هدر پراکسی می‌توان (به‌صورت موقت و بدون افشای داده) در response هدر `/api/health/` مقدار `request.META.get("HTTP_X_FORWARDED_PROTO")` را برگرداند؛ اما این نیازمند **تغییر کد** است و در این مرحله انجام نمی‌شود.

---

## ۸. گزارش نهایی

### ۸.۱ یافته‌های تأییدشده (Confirmed)
1. مقدار `SECURE_SSL_REDIRECT` در مخزن **`not DEBUG`** است ([settings.py L72](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L72)) → در تولید `True`.
2. تغییر «`SECURE_SSL_REDIRECT = False`» **در `settings.py` وجود ندارد**؛ تنها در فایل‌های تست ([test_settings.py L12](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/test_settings.py#L12)، [integration_test_settings.py L10](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/integration_test_settings.py#L10)) که در تولید بارگذاری نمی‌شوند.
3. تنها میدل‌ور فعال‌کنندهٔ ریدایرکت روی `/`، `SecurityMiddleware` است ([settings.py L19-20](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L19-L20)).
4. هیچ `redirect()`/`HttpResponseRedirect`/`HttpResponsePermanentRedirect` در بک‌اند و هیچ ریدایرکت سرورساید در فرانت وجود ندارد (جدول بخش ۳).
5. `SECURE_PROXY_SSL_HEADER` فقط با `TRUST_PROXY_PROTO=True` فعال می‌شود ([settings.py L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83)).
6. تنها مسیر معاف از ریدایرکت: `/api/health/` ([settings.py L75](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L75)، [health.py L34](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py#L34)).
7. Gunicorn کانتینر فقط HTTP سرو می‌کند (بدون TLS) → `wsgi.url_scheme == http` ([gunicorn.conf.py L1](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py#L1)).
8. `APPEND_SLASH` (پیش‌فرض True) به‌دلیل catch-all بی‌اثر است؛ `PREPEND_WWW`/`USE_X_FORWARDED_HOST` تعریف نشده‌اند ([urls.py L15](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/urls.py#L15)، [settings.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py)).
9. `Dockerfile` هیچ `HOME` تعریف نکرده و کاربر بدون home ساخته می‌شود ([Dockerfile L10-14, L21](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile#L10-L21)) → وابستگی سوکت کنترل Gunicorn به `HOME`.

### ۸.۲ فرضیه‌های قوی (Strong hypotheses)
- **HY1:** حلقه از `SecurityMiddleware` می‌آید: درخواستِ تحویلی به Django از نظر scheme «http» تلقی می‌شود (هدر `X-Forwarded-Proto: https` نمی‌رسد یا `TRUST_PROXY_PROTO` مؤثر نیست)، پس `301 → https` صادر و بی‌پایان تکرار می‌شود.
- **HY2:** تغییر موقت `SECURE_SSL_REDIRECT=False` هرگز مؤثر نشده (deploy نشده یا در فایل اشتباه).
- **HY3:** احتمالاً پراکسی دارکوب خود نیز ریدایرکت/نرمال‌سازی انجام می‌دهد؛ در این حالت حتی با اپ درست، حلقه می‌ماند.

### ۸.۳ رفتار نامعلوم زیرساخت دارکوب (Unknown — نیازمند شاهد)
- پروتکل تحویلی به کانتینر؛ وجود/نام/مقدار/نحوهٔ بازنویسی هدر proto؛ تعداد hopهای زنجیره؛ رفتار ریدایرکت خود پراکسی؛ مقدار `Host`. (بخش ۴.۲)

### ۸.۴ شواهد کد با مسیر و شمارهٔ خط
همه در بخش‌های ۱ و ۳ با لینک مستقیم آمده است؛ موارد حیاتی:
[settings.py L72](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L72) · [L75](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L75) · [L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83) · [urls.py L14-15](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/urls.py#L14-L15) · [gunicorn.conf.py L1-4](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py#L1-L4) · [Dockerfile L21](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile#L21) · [health.py L26-36](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/health.py#L26-L36) · [security.py L82-114](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/core/security.py#L82-L114).

### ۸.۵ نمودار جریان ریدایرکت
```
                ┌──────────────────────────────────────────────────────────┐
                │ مرورگر: GET https://okhovat.darkube.ir/                  │
                └───────────────────────────┬──────────────────────────────┘
                                            │ TLS
                                            ▼
        ┌──────────────────────────────────────────────────────────────┐
        │ پراکسی دارکوب (TLS termination)                              │
        │  - آیا هدر X-Forwarded-Proto را ست/بازنویسی می‌کند؟ UNKNOWN   │
        │  - آیا خودش ریدایرکت HTTP→HTTPS دارد؟ UNKNOWN                │
        └───────────────────────────┬──────────────────────────────────┘
                                    │ HTTP (plain) به :8000
                                    ▼
        ┌──────────────────────────────────────────────────────────────┐
        │ Gunicorn (0.0.0.0:8000, بدون TLS) → wsgi.url_scheme = "http" │
        └───────────────────────────┬──────────────────────────────────┘
                                    ▼
   MIDDLEWARE[0] SecurityMiddleware:
     is_secure() == https  ?  ──► بله → ادامه (200 در نهایت)
        │                          (تنها وقتی که SECURE_PROXY_SSL_HEADER
        │                           فعال است و هدر == "https")
        └─► خیر و SECURE_SSL_REDIRECT=True و مسیر ≠ ^api/health/$
                    │
                    ▼
        301 Location: https://okhovat.darkube.ir/<same path>
                    │
                    └──────► مرورگر دوباره https می‌طلبد ──► (برگشت به بالا)
                             ⇒ تکرار بی‌پایان ⇒ ERR_TOO_MANY_REDIRECTS

   نکته: /api/health/ ⇒ معاف (SECURE_REDIRECT_EXEMPT + ReadinessMiddleware)
         ⇒ readiness می‌تواند سالم باشد درحالی‌که همه‌چیز حلقه دارد.
```

### ۸.۶ فهرست دستورهای تشخیصی
همان بخش ۷ (الف: از Windows PowerShell؛ ب: از ترمینال کانتینر). همه فقط-خواندنی.

### ۸.۷ رتبه‌بندی علل احتمالی ریشه‌ای
1. **نرسیدن هدر معتبر `X-Forwarded-Proto: https` به Django** در حالی‌که `SECURE_SSL_REDIRECT=True` فعال است (HY1) — بالاترین احتمال.
2. **عدم‌اعمال/عدم‌deploy شدن `TRUST_PROXY_PROTO=True`** (یا اعمال تغییر موقت در فایل اشتباه) (HY2).
3. **ریدایرکت مستقل خود پراکسی دارکوب** (HY3).
4. **مقدار ترکیبی/append شدهٔ هدر** که تطبیق برابری را می‌شکند (زیرمجموعهٔ HY1).
5. کش `301` مرورگر / HSTS یک‌ساله که تشخیص را پنهان می‌کند (محرک نیست، ولی بازتولید را گمراه می‌کند).

### ۸.۸ برنامهٔ اصلاح حداقلی و ایمن (فقط پس از تأیید ریشه)
اصل پیش‌فرض: **هیچ محافظتی غیرفعال نشود** (نه HTTPS، نه کوکی‌های Secure، نه CSRF، نه HSTS). فقط «اعتماد به پراکسی» درست تنظیم شود.

1. **راستی‌آزمایی مقادیر مؤثر** با دستور ۳ در بخش ۷-ب (ایمیج در حال اجرا) و بررسی اینکه نسخهٔ مستقر همان commit موردنظر است.
2. **تعیین دقیق هدر پراکسی** (نام + مقدار + replace/append) از مستندات/پشتیبانی دارکوب یا با یک probe موقت فقط-خواندنی.
   - اگر دارکوب `X-Forwarded-Proto: https` می‌فرستد → تنها اقدام لازم: ست‌کردن `TRUST_PROXY_PROTO=True` و **اطمینان از deploy**؛ کد نیازی به تغییر ندارد.
   - اگر نام هدر متفاوت است → تغییر **فقط** [settings.py L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83) به همان هدر/مقدار.
   - اگر دارکوب هیچ هدری نمی‌فرستد و قابل‌تنظیم نیست → اجبار HTTPS در پراکسی و سپس (و فقط در این حالت) `SECURE_SSL_REDIRECT=False`؛ با آگاهی از حذف defense-in-depth در لایهٔ اپ.
3. **`TRUSTED_PROXY_COUNT`** را فقط با شاهد (بازنویسی `X-Forwarded-For` توسط پراکسی و تعداد hop واقعی) تنظیم کنید؛ نه با حدس.
4. **پایداری `HOME` (جدا از حلقه):** افزودن `ENV HOME=/tmp` به [Dockerfile](file:///c:/Users/moham/Desktop/okhovat-react-django/Dockerfile#L10-L14) و/یا `worker_tmp_dir="/tmp"` به [gunicorn.conf.py](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/gunicorn.conf.py) تا سوکت کنترل Gunicorn به متغیر پلتفرم وابسته نباشد.
5. **معیار پذیرش:** `curl.exe -sS -L -o NUL -w "%{num_redirects} %{http_code}" https://okhovat.darkube.ir/` حداکثر ≤۱ ریدایرکت و کد نهایی `200` بدهد؛ `/assets/logo-ui.webp` هم `200` شود؛ و `SECURE_SSL_REDIRECT`/کوکی‌های امن/CSRF/HSTS دست‌نخورده بمانند.
6. **نکتهٔ HSTS:** در طول دیباگ، برای مرورگرهای آزمایش، HSTS کش‌شده را پاک کنید (`chrome://net-internals/#hsts`) یا از پنجرهٔ ناشناس/مرورگر دیگر استفاده کنید تا نتیجهٔ واقعی دیده شود. (HSTS را به‌عنوان راه‌حل دائمی غیرفعال نکنید.)

---

### جمع‌بندی یک‌خطی
منبع کد-سطحیِ حلقه **`SecurityMiddleware` با `SECURE_SSL_REDIRECT=True`** است ([settings.py L72](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L72)) و شرط رفع آن، رسیدن هدر معتبر پروتو از پراکسی دارکوب و فعال‌بودن مؤثر `TRUST_PROXY_PROTO` است ([settings.py L82-83](file:///c:/Users/moham/Desktop/okhovat-react-django/backend/config/settings.py#L82-L83))؛ رفع قطعی نیازمند **تأیید runtime رفتار هدر پراکسی** است و نباید با حدس یا با خاموش‌کردن امنیت انجام شود.
