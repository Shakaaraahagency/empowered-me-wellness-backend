from datetime import datetime, timedelta, timezone

from extensions import db
from models.booking import Booking
from models.class_ import Session
from services.email_service import send_booking_reminder

REMINDER_WINDOW_HOURS = 24


def send_due_reminders() -> list:
    """
    Finds confirmed bookings for sessions starting within the next
    REMINDER_WINDOW_HOURS that haven't had a reminder sent yet, sends one,
    and marks them so this is safe to run repeatedly (e.g. from a daily
    cron job) without double-emailing anyone.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    window_end = now + timedelta(hours=REMINDER_WINDOW_HOURS)

    due = (
        Booking.query.join(Session)
        .filter(
            Booking.status == "confirmed",
            Booking.reminder_sent_at.is_(None),
            Session.start_time >= now,
            Session.start_time <= window_end,
            Session.status == "scheduled",
        )
        .all()
    )

    sent = []
    for booking in due:
        send_booking_reminder(booking)
        booking.reminder_sent_at = datetime.now(timezone.utc)
        sent.append(booking.id)

    db.session.commit()
    return sent
