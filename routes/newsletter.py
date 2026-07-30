import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from extensions import db, limiter
from models.newsletter import NewsletterSubscriber

newsletter_bp = Blueprint("newsletter", __name__, url_prefix="/api/v1/newsletter")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


@newsletter_bp.route("/subscribe", methods=["POST"])
@limiter.limit("10 per minute")
def subscribe():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if not email or not EMAIL_RE.match(email):
        return _error("Please provide a valid email address.", "invalid_email", 400)

    existing = NewsletterSubscriber.query.filter_by(email=email).first()
    if existing:
        if existing.status == "unsubscribed":
            existing.status = "active"
            existing.unsubscribed_at = None
            db.session.commit()
        return jsonify({"subscribed": True}), 200

    sub = NewsletterSubscriber(email=email)
    db.session.add(sub)
    db.session.commit()
    return jsonify({"subscribed": True}), 201


@newsletter_bp.route("/unsubscribe", methods=["POST"])
@limiter.limit("10 per minute")
def unsubscribe():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    sub = NewsletterSubscriber.query.filter_by(email=email).first()
    if sub and sub.status == "active":
        sub.status = "unsubscribed"
        sub.unsubscribed_at = datetime.now(timezone.utc)
        db.session.commit()

    # Same response whether they were subscribed or not — don't confirm
    # which, same principle as auth/contact endpoints elsewhere.
    return jsonify({"unsubscribed": True}), 200
