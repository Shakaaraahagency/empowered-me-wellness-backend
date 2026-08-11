import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request

from extensions import db, limiter
from models.user import User
from models.product import Product
from models.order import Order, OrderItem
from serializers.order_serializer import serialize_order
from services.payment_service import create_checkout_session, verify_webhook_signature, PaymentError
from services.download_service import generate_download_token, verify_download_token, resolve_file_path
from middleware.ownership_required import ownership_required

orders_bp = Blueprint("orders", __name__, url_prefix="/api/v1")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _current_user_optional():
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            return User.query.get(identity)
    except Exception:
        pass
    return None


@orders_bp.route("/checkout", methods=["POST"])
@limiter.limit("10 per minute")
def checkout():
    data = request.get_json(silent=True) or {}
    product_ids = data.get("product_ids") or []

    if not product_ids or not isinstance(product_ids, list):
        return _error("At least one product is required.", "missing_products", 400)

    user = _current_user_optional()
    guest_email = None

    if not user:
        guest_email = (data.get("guest_email") or "").strip().lower()
        if not guest_email or not EMAIL_RE.match(guest_email):
            return _error("A valid email is required for guest checkout.", "invalid_email", 400)

    products = Product.query.filter(Product.id.in_(product_ids), Product.is_active.is_(True)).all()
    if len(products) != len(set(product_ids)):
        return _error("One or more products could not be found.", "invalid_products", 400)

    total = sum(p.price for p in products)

    order = Order(
        user_id=user.id if user else None,
        guest_email=guest_email,
        total_amount=total,
        status="pending",
    )
    db.session.add(order)
    db.session.flush()  # get order.id before creating items

    for p in products:
        db.session.add(OrderItem(order_id=order.id, product_id=p.id, price_at_purchase=p.price))

    db.session.commit()

    # These would be real frontend URLs in production; the frontend passes
    # its own origin so this stays environment-agnostic.
    success_url = data.get("success_url") or "https://example.com/order-confirmation.html"
    cancel_url = data.get("cancel_url") or "https://example.com/shop.html"
    success_url = f"{success_url}{'&' if '?' in success_url else '?'}order_id={order.id}"

    try:
        result = create_checkout_session(order, success_url, cancel_url)
    except PaymentError as e:
        return _error(e.message, e.code, 503)

    return jsonify({"order_id": order.id, "checkout_url": result["checkout_url"]}), 201


@orders_bp.route("/checkout/webhook", methods=["POST"])
def checkout_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = verify_webhook_signature(payload, sig_header)
    except PaymentError as e:
        return _error(e.message, e.code, 400)
    except Exception as e:
        import logging
        logging.getLogger("emw").exception("Unexpected error verifying Stripe webhook signature")
        return _error(str(e), "webhook_verification_failed", 400)

    try:
        if event.get("type") == "checkout.session.completed":
            from datetime import datetime, timezone
            import logging
            logger = logging.getLogger("emw")

            session = event.get("data", {}).get("object", {})
            metadata = session.get("metadata") or {}

            # 1. Product Order Checkout
            order_id = metadata.get("order_id")
            if order_id:
                order = db.session.get(Order, order_id) or Order.query.get(order_id)
                if order and order.status != "paid":
                    order.status = "paid"
                    order.paid_at = datetime.now(timezone.utc)
                    db.session.commit()
                    logger.info("Webhook successfully marked order %s as paid", order.id)

            # 2. Session Event Booking Checkout
            booking_id = metadata.get("booking_id")
            if booking_id:
                from models.booking import Booking
                booking = db.session.get(Booking, booking_id) or Booking.query.get(booking_id)
                if booking and booking.status == "pending":
                    booking.status = "confirmed"
                    db.session.commit()
                    logger.info("Webhook successfully marked booking %s as confirmed", booking.id)
                    try:
                        from services.email_service import send_booking_confirmation
                        send_booking_confirmation(booking)
                    except Exception:
                        logger.exception("Webhook confirmed booking %s but confirmation email failed.", booking.id)

        return jsonify({"received": True}), 200
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger("emw").exception("Unhandled exception in checkout_webhook: %s", str(e))
        return jsonify({"error": {"message": str(e), "code": "webhook_processing_error"}}), 500


@orders_bp.route("/orders/mine", methods=["GET"])
@jwt_required()
def my_orders():
    identity = get_jwt_identity()
    orders = Order.query.filter_by(user_id=identity).order_by(Order.created_at.desc()).all()
    from services.payment_service import sync_order_payment_status

    for o in orders:
        if o.status == "pending":
            sync_order_payment_status(o)

    return jsonify([serialize_order(o) for o in orders]), 200


@orders_bp.route("/orders/<order_id>", methods=["GET"])
@ownership_required(lambda order_id: Order.query.get(order_id))
def get_order(order_id, resource):
    if resource.status == "pending":
        from services.payment_service import sync_order_payment_status
        sync_order_payment_status(resource)

    return jsonify(serialize_order(resource)), 200


@orders_bp.route("/orders/<order_id>/download/<product_id>", methods=["GET"])
@ownership_required(lambda order_id, product_id: Order.query.get(order_id))
def get_download_link(order_id, product_id, resource):
    if resource.status == "pending":
        from services.payment_service import sync_order_payment_status
        sync_order_payment_status(resource)

    return _issue_download_link(resource, product_id)


@orders_bp.route("/orders/<order_id>/guest-download/<product_id>", methods=["GET"])
@limiter.limit("10 per minute")
def get_guest_download_link(order_id, product_id):
    """
    Guests have no account to authenticate a download request with, so
    ownership_required (which needs a JWT) doesn't apply here. Instead this
    requires knowing BOTH the order_id — a random UUID only ever shown to
    the purchaser, once, at checkout — AND the email address on file for
    that order. Neither alone is enough; this is the same 'verify by email'
    pattern most e-commerce guest order lookups use.
    """
    email = (request.args.get("email") or "").strip().lower()
    order = Order.query.get(order_id)

    if not order or order.user_id is not None:
        # Same generic error whether the order doesn't exist or it belongs
        # to a real account (which must use the authenticated route instead)
        # — don't confirm which case it is.
        return _error("Order not found.", "not_found", 404)

    if not email or order.guest_email != email:
        return _error("Order not found.", "not_found", 404)

    return _issue_download_link(order, product_id)


def _issue_download_link(order, product_id):
    if order.status != "paid":
        return _error("This order has not been paid yet.", "order_not_paid", 402)

    owns_product = any(item.product_id == product_id for item in order.items)
    if not owns_product:
        return _error("This product isn't part of that order.", "product_not_in_order", 403)

    token = generate_download_token(order.id, product_id)
    return jsonify({"download_url": f"/api/v1/files/download/{token}"}), 200


@orders_bp.route("/files/download/<token>", methods=["GET"])
@limiter.limit("20 per minute")
def download_file(token):
    try:
        data = verify_download_token(token)
    except ValueError as e:
        return _error(str(e), "invalid_download_token", 403)

    product = Product.query.get(data["product_id"])
    if not product:
        return _error("File not found.", "not_found", 404)

    import cloudinary.utils
    from flask import redirect
    try:
        # Generate a signed URL valid for 1 hour (3600 seconds)
        signed_url = cloudinary.utils.cloudinary_url(
            product.file_path,
            resource_type="raw",
            type="authenticated",
            sign_url=True,
            expires_at=int(datetime.now(timezone.utc).timestamp()) + 3600
        )[0] # cloudinary_url returns a tuple (url, options)
        return redirect(signed_url)
    except Exception as e:
        return _error(f"Could not generate secure download link: {str(e)}", "download_failed", 500)
