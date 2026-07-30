import logging

from flask import Blueprint, jsonify, request

from extensions import db
from models.booking import Booking
from serializers.booking_serializer import serialize_booking
from middleware.admin_required import admin_required

bookings_admin_bp = Blueprint("bookings_admin", __name__, url_prefix="/api/v1/admin/bookings")
logger = logging.getLogger("emw")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


@bookings_admin_bp.route("", methods=["GET"])
@admin_required
def list_bookings():
    status_filter = request.args.get("status")
    query = Booking.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    bookings = query.order_by(Booking.created_at.desc()).limit(200).all()
    return jsonify([serialize_booking(b) for b in bookings]), 200


@bookings_admin_bp.route("/<booking_id>/attendance", methods=["PATCH"])
@admin_required
def mark_attendance(booking_id):
    booking = Booking.query.get(booking_id)
    if not booking:
        return _error("Booking not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("attended", "no_show"):
        return _error("status must be 'attended' or 'no_show'.", "invalid_status", 400)

    booking.status = status
    db.session.commit()
    return jsonify(serialize_booking(booking)), 200


@bookings_admin_bp.route("/<booking_id>/cancel", methods=["PATCH"])
@admin_required
def admin_cancel_booking(booking_id):
    """Admin override — unlike the client-facing cancel, this ignores the
    24-hour policy window (Latoya may need to cancel a booking for
    operational reasons regardless of timing) but still notifies the
    affected client."""
    from services.email_service import send_cancellation_notice

    booking = Booking.query.get(booking_id)
    if not booking:
        return _error("Booking not found.", "not_found", 404)
    if booking.status != "confirmed":
        return _error("This booking is not active.", "booking_not_active", 400)

    from datetime import datetime, timezone

    booking.status = "cancelled"
    booking.cancelled_at = datetime.now(timezone.utc)
    db.session.commit()

    send_cancellation_notice(booking)

    return jsonify(serialize_booking(booking)), 200
