import logging

import stripe
from flask import current_app

logger = logging.getLogger("emw")


class PaymentError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


def _stripe_configured() -> bool:
    return bool(current_app.config.get("STRIPE_SECRET_KEY"))


def create_checkout_session(order, success_url: str, cancel_url: str) -> dict:
    """
    Returns {"checkout_url": ...}.

    If STRIPE_SECRET_KEY is configured, this makes a real call to Stripe.
    If it isn't (local dev without keys), this runs a DEV-ONLY SIMULATION
    that marks the order paid immediately and points straight at the
    success URL — loudly logged so nobody mistakes it for the real thing.
    This mirrors the SQLite dev-fallback pattern already used elsewhere in
    this codebase: never active in production (enforced below), always
    active for local iteration without needing real payment credentials.
    """
    if current_app.config.get("FLASK_ENV") == "production" and not _stripe_configured():
        # Production must never silently fall back to the simulation.
        raise PaymentError(
            "Payments are not configured yet. Please try again later.",
            "payments_not_configured",
        )

    if not _stripe_configured():
        logger.warning(
            "DEV-ONLY PAYMENT SIMULATION: Stripe is not configured, so order %s "
            "is being marked paid immediately without a real payment. This path "
            "is disabled in production by the check above.",
            order.id,
        )
        from extensions import db
        from datetime import datetime, timezone

        order.status = "paid"
        order.paid_at = datetime.now(timezone.utc)
        db.session.commit()
        return {"checkout_url": success_url, "simulated": True}

    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]

    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {"name": item.product.name},
                "unit_amount": int(item.price_at_purchase * 100),
            },
            "quantity": 1,
        }
        for item in order.items
    ]

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"order_id": order.id},
            customer_email=order.contact_email() or None,
        )
    except stripe.error.StripeError as e:
        logger.exception("Stripe checkout session creation failed")
        raise PaymentError("Could not start checkout. Please try again.", "stripe_error") from e

    order.stripe_checkout_session_id = session.id
    from extensions import db

    db.session.commit()

    return {"checkout_url": session.url, "simulated": False}


def create_session_booking_checkout_session(session_model, booking, customer_email: str, success_url: str, cancel_url: str) -> dict:
    """
    Creates a Stripe Checkout Session for a paid class/event booking.
    """
    if current_app.config.get("FLASK_ENV") == "production" and not _stripe_configured():
        raise PaymentError(
            "Payments are not configured yet. Please try again later.",
            "payments_not_configured",
        )

    if not _stripe_configured():
        logger.warning(
            "DEV-ONLY PAYMENT SIMULATION: Stripe is not configured, so booking %s "
            "is being marked confirmed immediately without real payment.",
            booking.id,
        )
        from extensions import db
        booking.status = "confirmed"
        db.session.commit()
        return {"checkout_url": success_url, "simulated": True}

    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]

    price_in_cents = int(round(float(session_model.price) * 100))

    line_items = [
        {
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Event Registration: {session_model.title}",
                    "description": session_model.description or f"Registration for {session_model.title}",
                },
                "unit_amount": price_in_cents,
            },
            "quantity": 1,
        }
    ]

    try:
        checkout_session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "type": "event_booking",
                "booking_id": str(booking.id),
                "session_id": str(session_model.id),
            },
            customer_email=customer_email or None,
        )
    except stripe.error.StripeError as e:
        logger.exception("Stripe checkout session creation failed for booking %s", booking.id)
        raise PaymentError("Could not start checkout. Please try again.", "stripe_error") from e

    return {"checkout_url": checkout_session.url, "simulated": False}


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verifies a Stripe webhook signature and returns the parsed event.
    Raises PaymentError on failure. This is pure local HMAC verification —
    no network call to Stripe is made here."""
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise PaymentError("Webhook is not configured.", "webhook_not_configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise PaymentError("Invalid webhook signature.", "invalid_signature") from e

    return event
