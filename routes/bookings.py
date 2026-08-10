import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request

from extensions import db, limiter
from models.user import User
from models.booking import Booking
from serializers.booking_serializer import serialize_booking
from services.booking_service import create_booking, cancel_booking, BookingError
from middleware.ownership_required import ownership_required

bookings_bp = Blueprint("bookings", __name__, url_prefix="/api/v1/bookings")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _current_user_optional():
    """Returns the logged-in user if a valid access token is present,
    otherwise None — used because booking supports both guest and
    logged-in flows on the same endpoint."""
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return User.query.get(identity)
    except Exception:
        pass
    return None


@bookings_bp.route("", methods=["POST"])
@limiter.limit("10 per minute")
def create_booking_route():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    if not session_id:
        return _error("session_id is required.", "missing_session_id", 400)

    user = _current_user_optional()
    guest_info = None

    if not user:
        name = (data.get("guest_name") or "").strip()
        email = (data.get("guest_email") or "").strip().lower()
        phone = (data.get("guest_phone") or "").strip() or None

        if not name or len(name) > 255:
            return _error("Please provide your name.", "invalid_name", 400)
        if not email or not EMAIL_RE.match(email):
            return _error("Please provide a valid email address.", "invalid_email", 400)

        guest_info = {"name": name, "email": email, "phone": phone}

    try:
        booking = create_booking(session_id, user=user, guest_info=guest_info)
    except BookingError as e:
        return _error(e.message, e.code, 409 if e.code == "session_full" else 400)

    # Check if this booking requires payment
    session_obj = booking.session
    if session_obj.price is not None and float(session_obj.price) > 0:
        from services.payment_service import create_booking_checkout_session, PaymentError

        success_url = data.get("success_url") or f"https://empoweredmewellness.com/booking-confirmation.html?id={booking.id}"
        cancel_url = data.get("cancel_url") or f"https://empoweredmewellness.com/session-detail.html?id={session_obj.id}"

        # Ensure order/booking ID and Stripe session_id placeholder are in success URL
        if "id=" not in success_url:
            success_url = f"{success_url}{'&' if '?' in success_url else '?'}id={booking.id}"
        if "session_id=" not in success_url:
            success_url = f"{success_url}&session_id={{CHECKOUT_SESSION_ID}}"

        try:
            result = create_booking_checkout_session(booking, success_url, cancel_url)
            return jsonify({"booking": serialize_booking(booking), "checkout_url": result["checkout_url"]}), 201
        except PaymentError as e:
            return _error(e.message, e.code, 503)

    return jsonify({"booking": serialize_booking(booking), "checkout_url": None}), 201


@bookings_bp.route("/<booking_id>/confirm-payment", methods=["POST"])
def confirm_booking_payment_route(booking_id):
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id") or request.args.get("session_id")
    from services.payment_service import verify_and_confirm_booking_payment

    booking = verify_and_confirm_booking_payment(booking_id, session_id)
    if not booking:
        return _error("Booking not found.", "not_found", 404)
    return jsonify(serialize_booking(booking)), 200


@bookings_bp.route("/mine", methods=["GET"])
@jwt_required()
def my_bookings():
    identity = get_jwt_identity()
    bookings = (
        Booking.query.filter_by(user_id=identity)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return jsonify([serialize_booking(b) for b in bookings]), 200


@bookings_bp.route("/<booking_id>", methods=["GET"])
@ownership_required(lambda booking_id: Booking.query.get(booking_id))
def get_booking(booking_id, resource):
    return jsonify(serialize_booking(resource)), 200


@bookings_bp.route("/<booking_id>/cancel", methods=["PATCH"])
@ownership_required(lambda booking_id: Booking.query.get(booking_id))
def cancel_booking_route(booking_id, resource):
    try:
        booking = cancel_booking(resource)
    except BookingError as e:
        return _error(e.message, e.code, 400)
    return jsonify(serialize_booking(booking)), 200
