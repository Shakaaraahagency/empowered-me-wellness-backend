from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from extensions import db
from models.contact_message import ContactMessage
from middleware.admin_required import admin_required
from services.audit_service import log_action

contact_admin_bp = Blueprint("contact_admin", __name__, url_prefix="/api/v1/admin/contact-messages")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _serialize(m):
    return {
        "id": m.id,
        "name": m.name,
        "email": m.email,
        "message": m.message,
        "status": m.status,
        "created_at": m.created_at.isoformat(),
    }


@contact_admin_bp.route("", methods=["GET"])
@admin_required
def list_messages():
    status_filter = request.args.get("status")
    query = ContactMessage.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    messages = query.order_by(ContactMessage.created_at.desc()).all()
    return jsonify([_serialize(m) for m in messages]), 200


@contact_admin_bp.route("/<message_id>", methods=["PATCH"])
@admin_required
def update_message_status(message_id):
    m = ContactMessage.query.get(message_id)
    if not m:
        return _error("Message not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in ("new", "read", "replied"):
        return _error("status must be 'new', 'read', or 'replied'.", "invalid_status", 400)

    m.status = status
    db.session.commit()
    log_action(
        "contact_message_status_changed",
        user_id=get_jwt_identity(),
        resource_type="contact_message",
        resource_id=m.id,
        detail=f"status={status}",
        request=request,
    )
    return jsonify(_serialize(m)), 200
