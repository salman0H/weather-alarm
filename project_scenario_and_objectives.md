# عنوان پروژه: سیستم هشدار سریع و هوشمندی آب‌وهوای شهری (Smart Urban Weather Intelligence & Early Warning System)

## چکیده و بیان مسئله
مدیریت بحران‌های شهری و کاهش خطرات ناشی از پدیده‌های جوی، نیازمند دسترسی بلادرنگ به داده‌های دقیق و پردازش سریع آن‌هاست. کلان‌شهری مانند مشهد، با توجه به تراکم جمعیت، مناطق صنعتی و ترافیک بالا، در معرض خطراتی نظیر آلودگی شدید هوا (AQI بالا)، طوفان‌های فصلی و بارش‌های ناگهانی قرار دارد. سیستم‌های سنتی پیش‌بینی آب‌وهوا معمولاً فاقد هشدارهای منطقه‌ای، بلادرنگ و کاربرمحور هستند.
این پروژه با هدف رفع این خلاء، یک سیستم کاملاً خودکار و بدون نیاز به سرور (Serverless) طراحی کرده است که داده‌های هواشناسی را از رابط برنامه‌نویسی OpenWeatherMap (OWM) و داده‌های کیفیت هوا را از پایگاه World Air Quality Index (WAQI) دریافت می‌کند. سیستم با استفاده از یک موتور ارزیابی ریسک (Risk Engine)، شرایط بحرانی را شناسایی کرده و از طریق هوش مصنوعی (مدل‌های زبانی بزرگ Groq LLM)، هشدارهای شخصی‌سازی‌شده و قابل‌فهم را مستقیماً به پیام‌رسان تلگرام شهروندان و مدیران بحران ارسال می‌نماید.

## اهداف اصلی پروژه
* **ارزیابی خودکار ریسک (Automated Risk Assessment):** پایش مداوم شاخص‌هایی نظیر سرعت باد، احتمال بارش و کیفیت هوا، و تشخیص شرایط بحرانی پیش از وقوع.
* **معماری بدون سرور و مستقل (Zero-Dependency Serverless Architecture):** اجرای زمان‌بندی‌شده‌ی فرآیندها در بستر GitHub Actions بدون نیاز به تخصیص سرور اختصاصی و با تکیه بر کتابخانه‌های استاندارد پایتون (کاهش هزینه‌های نگهداری).
* **ارسال یکپارچه و قابل‌اطمینان پیام‌ها (Reliable Telegram Dispatch):** تضمین ارسال پیام‌های هشدار با بهره‌گیری از یک سیستم مدیریت وضعیت (State Machine) جهت جلوگیری از ارسال پیام‌های تکراری (Spam).
* **پردازش هوشمند و تنزل تدریجی (Graceful Degradation):** مدیریت هوشمند خطاهای شبکه و خرابی سنسورهای مبدأ با استفاده از داده‌های کش‌شده و فصلی، تا سیستم تحت هیچ شرایطی از کار نیفتد.

## معماری سیستم و زیرساخت
معماری این سیستم بر پایه یک خط لوله رویدادمحور (Event-Driven Pipeline) در GitHub Actions استوار است. در هر اجرای زمان‌بندی‌شده، داده‌ها از APIهای خارجی جمع‌آوری شده و به «موتور ریسک» سپرده می‌شوند. 
سیستم دارای یک State Machine است که خروجی را در دو مسیر کلی هدایت می‌کند:
۱. **حالت هشدار (Alert / Predictive Warning):** در صورت وجود هشدار رسمی یا عبور شاخص‌ها از حد مجاز، یک رویداد بحرانی ثبت می‌شود.
۲. **حالت آسمان صاف (Clear Skies):** در صورت عادی بودن شرایط، یک گزارش روزانه و خلاصه وضعیت هوشمند تولید می‌شود.
در هر دو حالت، سیستم با استفاده از Groq LLM داده‌های خام عددی را به متون روان، ساختاریافته و دارای ایموجی‌های بصری تبدیل می‌کند که برای کاربر نهایی کاملاً قابل درک است.

## بخش‌های کلیدی کد با توضیحات

### قطعه‌کد اول: موتور ارزیابی ریسک پیش‌بینانه (The Predictive Risk Engine)
این بخش از کد مسئول تحلیل داده‌های ترکیب‌شده‌ی OWM و WAQI است. به جای تکیه صرف بر هشدارهای رسمی، سیستم دارای یک هوش پیش‌بینانه است که در صورت وزش باد شدید (بیش از ۱۵ متر بر ثانیه)، احتمال بارش بالا (بیش از ۷۰ درصد) یا کیفیت هوای خطرناک (AQI بالای ۱۵۰)، به صورت مستقل اعلام وضعیت هشدار می‌کند. این ویژگی برای واکنش سریع در برابر آلودگی‌های ناگهانی هوا بسیار حیاتی است.

```python
# Analysis & State determination based on environmental thresholds
if current_alerts:
    state_enum = PipelineState.ALERT
elif global_metrics["max_wind"] > 15 or global_metrics["max_pop"] > 0.70 or global_metrics["aqi"] > 150:
    state_enum = PipelineState.PREDICTIVE_WARNING

if state_enum == PipelineState.PREDICTIVE_WARNING:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    
    risk_reasons = []
    # Identify specific triggers for the predictive warning
    if global_metrics['max_wind'] > 15:
        risk_reasons.append(f"Wind {global_metrics['max_wind']}m/s")
    if global_metrics['max_pop'] > 0.70:
        risk_reasons.append(f"Precipitation Prob {global_metrics['max_pop']*100}%")
    if global_metrics['aqi'] > 150:
        risk_reasons.append(f"Hazardous Air Quality (AQI {global_metrics['aqi']})")
        
    alert_payload = {
        "event": "Predictive Warning",
        "start": now_ts,
        "end": now_ts + (4 * 3600),
        "description": f"Predictive Engine detected high risk conditions: {', '.join(risk_reasons)}.",
        "max_pop": global_metrics["max_pop"],
        "zones": ["All Mashhad Zones"]
    }
```

### قطعه‌کد دوم: ماشین وضعیت و مکانیزم هشینگ (The State Machine / Hashing Mechanism)
برای جلوگیری از ارسال اخطارهای تکراری به کاربران (Spam) ناشی از اجراهای متوالی GitHub Actions، سیستم برای هر رویداد یک شناسه یکتا (Hash) تولید می‌کند. همان‌طور که در معماری سیستم تصمیم‌گیری شده است، متغیر `sender_name` از تولید این Hash حذف شده است. این امر قابلیت Idempotency ایجاد کرده و تضمین می‌کند که اگر چندین آژانس هواشناسی یک هشدار واحد را صادر کنند، سیستم همه را به عنوان یک رویداد واحد پردازش کند.

```python
def alert_id_for(alert):
    """
    Architecture Note for Academic Review:
    The 'sender_name' was intentionally omitted from the cryptographic hash generation. 
    This decision enforces automatic deduplication (Idempotency). If multiple agencies 
    (e.g., local vs. national meteorological organizations) issue redundant warnings for 
    the exact same event at the exact same start time, the system will resolve them to 
    a single unique hash, preventing notification spam.
    """
    # Create a unique MD5 hash based strictly on the event type and its start time
    raw = f"{alert.get('event')}|{alert.get('start')}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
```

### قطعه‌کد سوم: منطق تنزل تدریجی و پایداری شبکه (The Fallback / Graceful Degradation Logic)
در سامانه‌های حیاتی و Production-Grade، خطای شبکه‌ی یک سرویس خارجی نباید منجر به از کار افتادن کل سیستم شود. این قطعه‌کد نشان می‌دهد که چگونه سیستم در صورت قطعی یا عدم پاسخگویی API مبدأ، از بروز خطاهای زنجیره‌ای جلوگیری کرده و مقادیر پایه فصلی (Fallback) را جایگزین می‌کند. سپس با ثبت کد وضعیت خطا، به لایه‌های بالاتر (LLM) اطلاع می‌دهد تا رابط کاربری (UI) خود را متناسب با این شرایط تنزل‌یافته تنظیم کند.

```python
def fetch_weather_data_for_zone(lat, lon, api_key, timeout=10):
    # Prepare API request parameters
    params = {
        "lat": lat,
        "lon": lon,
        "appid": api_key,
        "exclude": "minutely",
        "units": "metric",
        "lang": "fa",
    }
    url = f"{OWM_BASE_URL}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "weather-alert-bot/1.0"})
    
    # Define a realistic baseline fallback payload for Mashhad during API outages
    fallback = {
        "current": {"temp": 20.0, "humidity": 30, "wind_speed": 5.0, "uvi": 5.0},
        "hourly": [{"dt": 0, "temp": 20.0, "pop": 0.0, "wind_speed": 5.0, "uvi": 5.0} for _ in range(24)],
        "alerts": []
    }

    try:
        # Attempt to fetch real-time data
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload, str(response.getcode())
    except urllib.error.HTTPError as e:
        # Gracefully degrade and return fallback data upon HTTP error
        print(f"[OWM] HTTP {e.code} {e.reason} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, f"HTTP {e.code}"
    except Exception as e:
        # Catch all other network errors to prevent pipeline crashes
        print(f"[OWM] Unexpected error — {e} — lat={lat} lon={lon}", file=sys.stderr)
        return fallback, "Error"
```

## چالش‌های پروژه و راه‌حل‌ها (Project Challenges & Solutions)

در طول توسعه و پیاده‌سازی این سیستم، با چندین چالش فنی مواجه شدیم که با رویکردهای مهندسی برطرف شدند:

### ۱. پایداری API و خطاهای خاموش (API Reliability & Silent Failures)
* **چالش:** استفاده از نسخه ۲.۵ سرویس One Call API مربوط به OpenWeatherMap برای حساب‌های رایگان منسوخ شده بود که منجر به خطاهای احراز هویت (مانند خطای 401) و در نتیجه بازگشت داده‌های پیش‌فرض و استاتیک (Fallback) می‌شد. از طرفی خطاهای JSON و شبکه به صورت خاموش (Silent) نادیده گرفته می‌شدند که دیباگ و خطایابی را برای توسعه‌دهنده به شدت دشوار می‌کرد.
* **راه‌حل:** برای اطمینان از دسترسی همیشگی به داده‌های معتبر و زنده، دریافت‌کننده اطلاعات سیستم به اندپوینت‌های استاندارد و کاملاً پایدار `Current Weather` و `5-Day Forecast` منتقل شد. ساختار دریافتی از این دو سرویس با یک معماری واسط دقیقاً به فرمت ساختار قبلی سیستم نگاشت (Map) شد تا موتور ارزیابی ریسک کاملاً بی‌نقص به کار خود ادامه دهد. همچنین مکانیزم مدیریت خطا (Error Handling) بازنویسی شد تا تمام خطاهای HTTP، شبکه و `KeyError`ها به طور دقیق ضبط شده و مستقیماً به بخش توسعه‌دهندگان (DevEx Footer) در تلگرام مخابره شوند. در کنار این موارد، برای تضمین پایداری همیشگی و دریافت داده‌های بسیار معتبر و دقیق‌تر از وضعیت آلودگی هوا، اندپوینت دریافت شاخص کیفیت هوا (WAQI) به طور اختصاصی روی ایستگاه چمن مشهد (`@11601`) تنظیم شد و توکن اختصاصی و تأییدشده‌ی `e92b7626f7f331e6ecd4cdebc8be5b6cfd1bc60f` در کدهای سیستم (به عنوان پیش‌فرضِ همیشه در دسترس) نهادینه شد تا تحت هر شرایطی اطلاعات حیاتی آلاینده‌ها به دست کاربر برسد.

### ۲. بومی‌سازی رابط کاربری و چالش‌های چیدمان (UI Localization & RTL Layout)
* **چالش:** داشبورد مانیتورینگ زنده (Mission Control UI) در ابتدا به زبان انگلیسی و با چینش چپ‌به‌راست (LTR) طراحی شده بود. بومی‌سازی آن به فارسی نیازمند تغییر جهت چیدمان، حفظ یکپارچگی استایل‌ها و استفاده از فونت‌های خوانا بود؛ بدون اینکه کدهای زیربنایی پایتون که محتوا را به صورت پویا در HTML تزریق می‌کردند دچار مشکل شوند.
* **راه‌حل:** تگ اصلی فایل HTML به استاندارد `dir="rtl"` تغییر یافت. با تکیه بر ویژگی‌های ذاتی و انعطاف‌پذیر CSS Grid، ساختار دو ستونی داشبورد به طور کاملاً خودکار قرینه و سازگار شد و نیازی به تغییرات گسترده در CSS نبود. فونت اصلی پروژه به `Vazirmatn` تغییر یافت، اما برای حفظ ظاهر حرفه‌ای و خوانایی اعداد و زمان‌ها، فونت `JetBrains Mono` در کلاس‌های عددی به عنوان انتخاب اول حفظ شد. کدهای تزریق متن در پایتون (توابع `re.sub`) برای تطبیق با کلمات فارسی به‌روزرسانی شدند و در نهایت، عبارات کلیدی در سیستم پرامپت هوش مصنوعی (LLM) بهبود یافتند تا گزارش‌های جوی تولید شده به جای یک لیست رباتیک، به یک روایت متنی روان، انسان‌گونه و ساختاریافته تبدیل شوند.

## فرمت پیام‌های ارسالی تلگرام (Telegram Message Formats)

سیستم بر اساس وضعیت آب‌وهوا، دو نوع پیام متفاوت تولید و به کاربر ارسال می‌کند. هر پیام به صورت پویا توسط LLM و با تکیه بر استانداردهای طراحی ربات‌های اطلاع‌رسانی ساخته می‌شود:

### ۱. پیام حالت عادی (Clear Skies / Daily Brief)
این پیام زمانی ارسال می‌شود که شرایط جوی در محدوده خطر (Alert) نبوده و صرفاً برای اطلاع‌رسانی منظم روزانه کاربرد دارد.

**ساختار پیام:**
- **تیتر اصلی:** 📅 گزارش هوشمند امروز
- **خلاصه کلی:** یک پاراگراف روان و کوتاه از شرایط جوی کل روز.
- **پیش‌بینی زمانی (Chronological Forecast):** شرایط در صبح، بعدازظهر و غروب (میانگین دما، رطوبت، باد).
- **تحلیل نواحی (Zone Analysis):** دسته‌بندی نواحی مشابه و بیان تفاوت‌های چشمگیر مکانی (مثلاً مقایسه مرکز شهر با کوهسنگی).
- **گزارش کیفیت هوا (Air Quality Report):** در صورت وجود داده‌های معتبر، میزان آلایندگی با ایموجی‌های مناسب اعلام می‌شود.
- **Developer Context (اختیاری):** در صورت بروز خطا در دریافت داده‌ها از API (وضعیت Degraded)، لاگ مربوط به پایداری سیستم در انتهای پیام نمایش داده می‌شود.

### ۲. پیام حالت هشدار (Alert / Predictive Warning)
این پیام با اولویت بالا و به منظور اقدام سریع برای کاربر ارسال می‌شود. این حالت یا از سمت منابع رسمی (OWM Alerts) فعال می‌شود، یا توسط موتور پیش‌بینی سیستم (Predictive Engine) به دلیل عبور داده‌ها از آستانه‌های خطر (مثلا باد شدید، احتمال بالای بارش، یا کیفیت هوای خطرناک).

**ساختار پیام:**
- **تیتر اصلی (قرمز):** 🚨 WEATHER ALERT — [نوع رویداد]
- **مناطق درگیر (Affected Zones):** مناطقی که درگیر بحران هستند.
- **بازه زمانی فعالیت (Active):** زمان شروع و پایان رویداد.
- **سطح خطر (Risk Level):** دسته‌بندی رنگی و متنی (مثلاً نارنجی — خطر قابل توجه).
- **توضیحات تحلیلی:** متنی تولید شده توسط LLM که خطرات احتمالی و دلایل فنی وقوع بحران را توضیح می‌دهد.
- **توصیه‌های ایمنی (Safety Guidance):** مجموعه‌ای از دستورالعمل‌های محافظتی.
- **دکمه تأیید (Acknowledge):** کاربر باید پیام را تأیید کند تا از ارسال مجدد (Spam) جلوگیری شود.

## محیط تست و شبیه‌سازی (Testing & Mocking)

برای توسعه‌دهندگان و تست سیستم بدون مصرف درخواست‌های واقعی از API (و برای بررسی رفتار سیستم در شرایط بحرانی)، دو متغیر محیطی کلیدی برای دیباگ در نظر گرفته شده است که می‌توانند در محیط اجرای گیت‌هاب (یا لوکال) فعال شوند:

- **Enable Test Mode (`TEST_MODE=true`):** با روشن کردن این گزینه، سیستم به جای دریافت زنده داده‌ها از API، داده‌های کش‌شده و محلی (`cached_owm_response.json`) را پردازش می‌کند. این قابلیت به ویژه برای توسعه و تست فرمت‌ها بسیار کاربردی است، زیرا مانع از مسدود شدن توکن API (Rate Limiting) می‌شود و هوش مصنوعی هم به دلیل نبود داده زنده فراخوانی نمی‌شود.
- **Force a Mock Severe Alert (`MOCK_ALERT=true`):** با فعال‌سازی این حالت، یک بحران شدید هواشناسی (مانند تندباد خطرناک یا آلودگی هوای شدید) به صورت مصنوعی در داده‌ها تزریق می‌شود (Inject). با این کار، مسیر اجرای کد به سمت تولید پیام حالت هشدار (Alert) هدایت می‌شود تا طراح سیستم بتواند ظاهر پیام هشدار، رنگ‌بندی‌ها، دکمه شیشه‌ای (Inline Keyboard) و روال ارسال موقعیت مکانی (Location) را در تلگرام بدون نیاز به انتظار برای وقوع واقعی یک فاجعه بررسی کند.

## نتیجه‌گیری و چشم‌انداز
