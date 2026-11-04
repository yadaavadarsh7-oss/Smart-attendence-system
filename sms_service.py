"""
SMS helper for SmartAttend.

Abhi API nahi hai, isliye default mode "dry_run" hai:
message asli mein nahi jata, sirf sms_log.txt mein likha jata hai.
API milne ke baad sirf neeche _send_via_provider() bharna hai
aur environment variable SMS_PROVIDER ko "live" karna hai.
"""
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SMS_LOG_FILE = os.path.join(BASE_DIR, "sms_log.txt")

# "dry_run" (default) ya "live"
SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "dry_run").lower()


def _log(phone, message, status):
    with open(SMS_LOG_FILE, "a", encoding="utf-8") as f:
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{stamp}] [{status}] +91{phone}: {message}\n")


def _send_via_provider(phone, message):
    """
    API milne ke baad yahan provider (Fast2SMS / MSG91 / Twilio) ka code likho.
    Success par True, fail par False return karo.
    API key hamesha environment variable se lo, code mein mat likho.
    """
    raise NotImplementedError("SMS API abhi configure nahi hai.")


def send_sms(phone, message):
    """Parent ko SMS bhejo. Returns (success: bool, info: str)."""
    phone = str(phone or "").strip()

    if not phone.isdigit() or len(phone) != 10:
        _log(phone, message, "SKIPPED_INVALID_NUMBER")
        return False, "invalid number"

    if SMS_PROVIDER != "live":
        _log(phone, message, "DRY_RUN")
        return True, "dry_run"

    try:
        ok = _send_via_provider(phone, message)
        _log(phone, message, "SENT" if ok else "FAILED")
        return bool(ok), "sent" if ok else "failed"
    except Exception as error:
        _log(phone, message, f"ERROR {error}")
        return False, str(error)
