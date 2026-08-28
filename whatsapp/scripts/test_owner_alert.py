"""Owner lead notification helpers."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

os.environ["TESTING"] = "true"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def run() -> int:
    from app.schemas import EnquiryFields
    from app.services.enquiry_service import (
        callback_datetime_from_fields,
        format_owner_lead_message,
        format_whatsapp_display,
        inquiry_completion_key,
        inquiry_is_complete_for_alert,
        notification_retry_due,
    )
    from app.services.whatsapp_client import normalize_phone

    failures: list[str] = []

    def fail(msg: str) -> None:
        failures.append(msg)
        print(f"  FAIL {msg}")

    def ok(msg: str) -> None:
        print(f"  OK   {msg}")

    fields = EnquiryFields(
        customer_name="Chetan",
        phone_number="9876543210",
        event_type="Wedding",
        event_date="26 September 2026",
        date_status="confirmed",
        guest_count=500,
        event_location="BTM Layout",
        venue_area="BTM Layout",
        meal_preference="To be discussed",
        special_requirements="None",
        callback_date="Tomorrow",
        callback_time="10 AM – 12 PM",
        preferred_callback="Tomorrow, 10 AM – 12 PM",
    )
    if not inquiry_is_complete_for_alert(fields):
        fail("Chetan fixture should be complete")
    else:
        ok("required inquiry fields pass completion check")

    if format_whatsapp_display("9876543210") != "+919876543210":
        fail(f"display phone {format_whatsapp_display('9876543210')}")
    else:
        ok("owner/customer display uses +91 format")

    if normalize_phone("+91 98765 43210") != "919876543210":
        fail("normalize_phone did not strip to WhatsApp digits")
    else:
        ok("provider send format is digits without spaces")

    enquiry = SimpleNamespace(
        customerName="Chetan",
        phoneNumber="919876543210",
        eventType="Wedding",
        eventDate=datetime(2026, 9, 26, 12, 0),
        eventLocation="BTM Layout",
        guestCount=500,
        preferredCallbackAt=datetime(2026, 8, 29, 10, 0),
        notes="Guest count requested: 500",
        dateStatus="confirmed",
        venueName=None,
        venueArea="BTM Layout",
        mealPreference="To be discussed",
        specialRequirements="None",
        callbackDate="Tomorrow",
        callbackTime="10 AM – 12 PM",
    )
    msg = format_owner_lead_message(enquiry, customer_phone="919876543210")
    for needle in ("NEW EVENT INQUIRY", "Chetan", "+919876543210", "Wedding", "26 September 2026", "500", "BTM Layout", "10 AM – 12 PM"):
        if needle not in msg:
            fail(f"owner message missing {needle!r}")
            break
    else:
        ok("owner WhatsApp copy includes lead details")

    k1 = inquiry_completion_key(fields, "919876543210")
    k2 = inquiry_completion_key(fields, "919876543210")
    if k1 != k2:
        fail("completion key not stable")
    else:
        ok("duplicate completion uses the same lead key")

    due = SimpleNamespace(
        notificationStatus="failed",
        notificationAttempts=1,
        lastNotificationAttempt=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=31),
    )
    if not notification_retry_due(due):
        fail("retry after 30s should be due")
    else:
        ok("failed owner alerts retry after 30 seconds")

    sent = SimpleNamespace(
        notificationStatus="sent",
        notificationAttempts=1,
        lastNotificationAttempt=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    if notification_retry_due(sent):
        fail("sent alerts must not retry")
    else:
        ok("successful owner alert is not sent twice")

    when = callback_datetime_from_fields(fields)
    if when.hour != 10:
        fail(f"callback datetime hour {when.hour} from 10 AM – 12 PM")
    else:
        ok("callback datetime uses 10 AM start")

    if failures:
        print("\nFAILED:")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nAll owner-alert checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
