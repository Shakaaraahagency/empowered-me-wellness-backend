from datetime import datetime, timezone, timedelta

from extensions import db
from models.class_ import Session
from models.booking import Booking

CANCELLATION_WINDOW_HOURS = 24
PENDING_BOOKING_EXPIRY_MINUTES = 10  # how long a pending booking holds a slot


class BookingError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


def create_booking(session_id: str, user=None, guest_info: dict | None = None) -> Booking:
    session = Session.query.get(session_id)
    if not session:
        raise BookingError("That session could not be found.", "session_not_found")

    if session.status != "scheduled":
        raise BookingError("This session is no longer available.", "session_unavailable")

    # The capacity check happens here, server-side, against the live count —
    # never trust a disabled button on the frontend to have enforced this.
    if session.is_full:
        raise BookingError("This session is fully booked.", "session_full")

    if not user and not guest_info:
        raise BookingError("Booking requires either an account or guest details.", "missing_identity")

    is_paid = session.price is not None and float(session.price) > 0
    initial_status = "pending" if is_paid else "confirmed"

    booking = Booking(session_id=session.id, status=initial_status)
    if is_paid:
        booking.expires_at = datetime.now(timezone.utc) + timedelta(minutes=PENDING_BOOKING_EXPIRY_MINUTES)
    if user:
        booking.user_id = user.id
    else:
        booking.guest_name = guest_info.get("name")
        booking.guest_email = guest_info.get("email")
        booking.guest_phone = guest_info.get("phone")

    db.session.add(booking)
    db.session.commit()

    # Send confirmation email immediately only for free sessions.
    # Paid sessions send email after Stripe payment completes via webhook.
    if not is_paid:
        try:
            from services.email_service import send_booking_confirmation
            send_booking_confirmation(booking)
        except Exception:
            import logging
            logging.getLogger("emw").exception(
                "Booking %s committed but confirmation email failed to send.", booking.id
            )

    return booking


def cancel_booking(booking: Booking) -> Booking:
    if booking.status != "confirmed":
        raise BookingError("This booking is not active.", "booking_not_active")

    session = booking.session
    hours_until_session = (
        session.start_time.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)
    ).total_seconds() / 3600

    if hours_until_session < CANCELLATION_WINDOW_HOURS:
        raise BookingError(
            f"Bookings can only be cancelled at least {CANCELLATION_WINDOW_HOURS} hours "
            "before the session starts.",
            "cancellation_window_passed",
        )

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    db.session.commit()
    return booking
