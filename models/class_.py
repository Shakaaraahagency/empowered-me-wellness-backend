from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class Class(db.Model):
    """A class 'type' — e.g. Kemetic Yoga for Beginners. Sessions are the
    actual bookable occurrences of a Class."""

    __tablename__ = "classes"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    category = db.Column(db.String(100), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    sessions = db.relationship("Session", backref="class_", lazy="dynamic")


class Session(db.Model):
    """A single bookable date/time occurrence."""

    __tablename__ = "sessions"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    class_id = db.Column(GUID(), db.ForeignKey("classes.id"), nullable=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False, default="Studio")
    capacity = db.Column(db.Integer, nullable=False, default=12)
    price = db.Column(db.Numeric(10, 2), nullable=True)  # null = free
    status = db.Column(db.String(20), nullable=False, default="scheduled")  # scheduled/closed/cancelled
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    bookings = db.relationship("Booking", backref="session", lazy="dynamic")

    @property
    def confirmed_booking_count(self) -> int:
        return self.bookings.filter_by(status="confirmed").count()

    @property
    def spots_remaining(self) -> int:
        return max(self.capacity - self.confirmed_booking_count, 0)

    @property
    def is_full(self) -> bool:
        return self.spots_remaining <= 0
