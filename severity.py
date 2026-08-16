"""
Alert severity classification — Inspired by the Met Office 3-tier system
(Yellow / Amber / Red) which combines likelihood and impact.

Since OpenWeatherMap doesn't provide an official severity field in alerts 
(only event and tags), this module maps event keywords to a severity level.
If another source provides an official severity later, this classify function 
can be replaced.
"""

SEVERITY_LEVELS = {
    "قرمز": {
        "emoji": "🔴",
        "label": "خطر بسیار جدی — اقدام فوری لازم است",
        "text_color": "#791F1F",
        "bg_color": "#FCEBEB",
        "keywords": ["سیل", "سیلاب", "طوفان شدید", "گردباد", "زلزله"]
    },
    "نارنجی": {
        "emoji": "🟠",
        "label": "خطر جدی — آمادگی لازم است",
        "text_color": "#633806",
        "bg_color": "#FAEEDA",
        "keywords": ["تگرگ", "باران شدید", "برف سنگین", "رعد و برق شدید"]
    },
    "زرد": {
        "emoji": "🟡",
        "label": "احتیاط — احتمال اختلال جزئی",
        "text_color": "#633806",
        "bg_color": "#FAEEDA",
        "keywords": ["گرمای شدید", "باد شدید", "مه غلیظ", "سرما"]
    }
}

DEFAULT_SEVERITY = "زرد"

SAFETY_TIPS = {
    "قرمز": [
        "از تردد در مسیل‌ها، زیرگذرها و مناطق کم‌ارتفاع خودداری کنید",
        "خودرو را در نقاط مرتفع پارک کنید",
        "در صورت امکان، محل سکونت را به نقطه امن منتقل کنید"
    ],
    "نارنجی": [
        "از رانندگی غیرضروری در ساعات اوج هشدار خودداری کنید",
        "وسایل نقلیه را از زیر درختان و تابلوهای ناپایدار دور نگه دارید",
        "درب و پنجره‌ها را محکم ببندید"
    ],
    "زرد": [
        "برنامه‌های بیرون از منزل را در صورت امکان به تعویق بیندازید",
        "از افراد سالمند و کودکان در این بازه زمانی مراقبت بیشتری کنید",
        "وسایل مورد نیاز (آب، شارژ موبایل) را آماده نگه دارید"
    ]
}


def classify_severity(event_text):
    """
    Determines the severity level based on keywords present in the event text.
    If no keywords match, DEFAULT_SEVERITY (زرد) is returned to ensure 
    no alert goes unclassified.
    """
    for level, info in SEVERITY_LEVELS.items():
        for keyword in info["keywords"]:
            if keyword in event_text:
                return level
    return DEFAULT_SEVERITY


def get_safety_tips(level):
    return SAFETY_TIPS.get(level, SAFETY_TIPS[DEFAULT_SEVERITY])
