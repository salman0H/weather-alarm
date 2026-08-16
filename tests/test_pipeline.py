"""
تست end-to-end با mock mode.

این تست چرخه کامل را بدون نیاز به هشدار واقعی هواشناسی و بدون نیاز به
کلید واقعی OpenWeatherMap بررسی می‌کند:

  ۱. یک alert از fixture خوانده می‌شود (dedupe و ساخت alert_id)
  ۲. برای یک subscriber فرضی، وضعیت از NO_ALERT به PENDING_ACK می‌رود
  ۳. شبیه‌سازی پیام /ok از کاربر -> وضعیت به ACKED می‌رود
  ۴. اجرای دوباره check بعد از ACKED -> هیچ ارسال جدیدی رخ نمی‌دهد
     (چون alert در fixture هنوز همان قبلی است)

اجرا: MOCK_ALERT=true python tests/test_pipeline.py
(کلیدهای API واقعی لازم نیستند چون send_message و generate_alert_message
 در این تست mock/monkeypatch می‌شوند تا هیچ درخواست شبکه واقعی زده نشود.)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import weather_alert_check as wac  # noqa: E402
import state as state_module  # noqa: E402

os.environ["MOCK_ALERT"] = "true"

SENT_MESSAGES = []


def fake_send_alert(telegram_token, groq_api_key, chat_id, alert):
    # به‌جای فراخوانی واقعی Groq و Telegram، فقط رویداد را ثبت می‌کنیم
    SENT_MESSAGES.append((chat_id, alert["event"]))
    return f"[mock message for {alert['event']}]"


def run():
    wac.send_alert = fake_send_alert  # monkeypatch برای جلوگیری از network call

    fresh_state = {"offset": 0, "subscribers": {"999": {"phone_number": None, "active_alert": None}}}

    current_alerts = wac.collect_alerts_across_zones(owm_api_key="unused-in-mock")
    assert len(current_alerts) == 1, "باید دقیقاً یک alert یکتا از fixture خوانده شود"

    subscriber = fresh_state["subscribers"]["999"]

    # مرحله ۱: اولین چک -> باید ارسال اولیه انجام شود
    wac.process_subscriber(subscriber, current_alerts, "tok", "key", "999", print)
    assert subscriber["active_alert"]["status"] == "PENDING_ACK"
    assert len(SENT_MESSAGES) == 1
    print("OK: ارسال اولیه انجام شد")

    # مرحله ۲: چک بلافاصله بعدی -> چون هنوز به RESEND_INTERVAL نرسیده، resend نباید بشود
    wac.process_subscriber(subscriber, current_alerts, "tok", "key", "999", print)
    assert len(SENT_MESSAGES) == 1, "نباید قبل از رسیدن به فاصله resend، دوباره ارسال شود"
    print("OK: resend زودهنگام رخ نداد")

    # مرحله ۳: شبیه‌سازی /ok کاربر
    subscriber["active_alert"]["status"] = "ACKED"
    print("OK: کاربر تایید کرد (شبیه‌سازی /ok)")

    # مرحله ۴: چک بعدی -> چون همان alert هنوز فعال است ولی وضعیت ACKED است، نباید resend شود
    wac.process_subscriber(subscriber, current_alerts, "tok", "key", "999", print)
    assert len(SENT_MESSAGES) == 1, "بعد از ACKED نباید همان alert دوباره ارسال شود"
    print("OK: بعد از تایید، ارسال مجدد متوقف شد")

    print("\nهمه تست‌ها با موفقیت پاس شدند.")


if __name__ == "__main__":
    run()
