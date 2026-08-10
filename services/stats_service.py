from datetime import datetime, timezone
from sqlalchemy import func

from extensions import db
from models.booking import Booking
from models.class_ import Session, Class
from models.order import Order


def get_overview_stats():
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    bookings_this_month = (
        Booking.query.filter(
            Booking.created_at >= month_start.replace(tzinfo=None),
            Booking.status == "confirmed",
        ).count()
    )

    product_revenue = (
        db.session.query(func.coalesce(func.sum(Order.total_amount), 0))
        .filter(Order.status == "paid", Order.created_at >= month_start.replace(tzinfo=None))
        .scalar()
    )

    booking_revenue = (
        db.session.query(func.coalesce(func.sum(Session.price), 0))
        .join(Booking, Booking.session_id == Session.id)
        .filter(
            Booking.status == "confirmed",
            Booking.created_at >= month_start.replace(tzinfo=None),
            Session.price.isnot(None),
        )
        .scalar()
    )

    total_revenue = float(product_revenue or 0) + float(booking_revenue or 0)

    upcoming_sessions = Session.query.filter(
        Session.status == "scheduled", Session.start_time >= now.replace(tzinfo=None)
    ).count()

    top_classes = (
        db.session.query(Class.name, func.count(Booking.id).label("booking_count"))
        .join(Session, Session.class_id == Class.id)
        .join(Booking, Booking.session_id == Session.id)
        .filter(Booking.status == "confirmed")
        .group_by(Class.name)
        .order_by(func.count(Booking.id).desc())
        .limit(5)
        .all()
    )

    pending_contact_messages = None
    from models.contact_message import ContactMessage

    pending_contact_messages = ContactMessage.query.filter_by(status="new").count()

    return {
        "bookings_this_month": bookings_this_month,
        "revenue_this_month": f"{total_revenue:.2f}",
        "upcoming_sessions": upcoming_sessions,
        "top_classes": [{"name": name, "bookings": count} for name, count in top_classes],
        "pending_contact_messages": pending_contact_messages,
    }
