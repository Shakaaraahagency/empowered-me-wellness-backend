import re

from flask import Blueprint, jsonify, request

from extensions import db, limiter
from models.contact_message import ContactMessage

contact_bp = Blueprint("contact", __name__, url_prefix="/api/v1/contact")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MAX_MESSAGE_LEN = 3000


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


@contact_bp.route("", methods=["POST"])
@limiter.limit("5 per minute")
def submit_contact():
    data = request.get_json(silent=True) or {}

    # Honeypot: a real user never fills this field in — it's visually
    # hidden by CSS in the frontend. A bot filling every field will trip it.
    if (data.get("website") or "").strip():
        # Return a fake success so the bot doesn't learn its submission was rejected.
        return jsonify({"submitted": True}), 201

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    message = (data.get("message") or "").strip()

    if not name or len(name) > 255:
        return _error("Please provide your name.", "invalid_name", 400)
    if not email or not EMAIL_RE.match(email):
        return _error("Please provide a valid email address.", "invalid_email", 400)
    if not message or len(message) > MAX_MESSAGE_LEN:
        return _error(
            f"Message must be between 1 and {MAX_MESSAGE_LEN} characters.",
            "invalid_message",
            400,
        )

    entry = ContactMessage(name=name, email=email, message=message)
    db.session.add(entry)
    db.session.commit()

    # Real email notification to Latoya wired up in Phase 6 (email_service).
    # For now the message is safely persisted and visible in the admin
    # dashboard once Phase 5 ships.

    return jsonify({"submitted": True}), 201
