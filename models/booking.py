from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)

    # Nullable because guests can book without an account. Guest contact
    # info is captured directly on the booking in that case.
    user_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=True)
    session_id = db.Column(GUID(), db.ForeignKey("sessions.id"), nullable=False)

    guest_name = db.Column(db.String(255), nullable=True)
    guest_email = db.Column(db.String(255), nullable=True)
    guest_phone = db.Column(db.String(50), nullable=True)
    stripe_checkout_session_id = db.Column(db.String(255), nullable=True, index=True)

    status = db.Column(db.String(20), nullable=False, default="confirmed")
    # confirmed / cancelled / attended / no_show

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    cancelled_at = db.Column(db.DateTime, nullable=True)
    reminder_sent_at = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)  # auto-cancel if unpaid by this time

    def contact_name(self) -> str:
        if self.user_id and self.user:
            return self.user.full_name
        return self.guest_name or "Guest"

    def contact_email(self) -> str:
        if self.user_id and self.user:
            return self.user.email
        return self.guest_email or ""


# Backref for convenience — defined here to avoid circular import ordering issues
from models.user import User  # noqa: E402

Booking.user = db.relationship("User", backref="bookings")
