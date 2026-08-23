import os
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from werkzeug.utils import secure_filename

from extensions import db
from models.class_ import Class, Session
from middleware.admin_required import admin_required
from serializers.session_serializer import serialize_class, serialize_session
from services.audit_service import log_action

sessions_admin_bp = Blueprint("sessions_admin", __name__, url_prefix="/api/v1/admin")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


# --- Classes ---

@sessions_admin_bp.route("/classes", methods=["GET"])
@admin_required
def list_classes_admin():
    classes = Class.query.order_by(Class.name).all()
    return jsonify([serialize_class(c) for c in classes]), 200


@sessions_admin_bp.route("/classes", methods=["POST"])
@admin_required
def create_class():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return _error("Class name is required.", "invalid_name", 400)

    c = Class(
        name=name,
        description=data.get("description"),
        image_url=data.get("image_url"),
        category=data.get("category"),
    )
    db.session.add(c)
    db.session.commit()
    log_action(
        "class_created",
        user_id=get_jwt_identity(),
        resource_type="class",
        resource_id=c.id,
        detail=c.name,
        request=request,
    )
    return jsonify({"id": c.id, "name": c.name}), 201


@sessions_admin_bp.route("/classes/<class_id>", methods=["PATCH"])
@admin_required
def update_class(class_id):
    c = Class.query.get(class_id)
    if not c:
        return _error("Class not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return _error("Class name cannot be empty.", "invalid_name", 400)
        c.name = name
    if "description" in data:
        c.description = data.get("description")
    if "category" in data:
        c.category = data.get("category")
    if "image_url" in data:
        c.image_url = data.get("image_url")
    if "is_active" in data:
        c.is_active = bool(data.get("is_active"))

    db.session.commit()
    log_action(
        "class_updated",
        user_id=get_jwt_identity(),
        resource_type="class",
        resource_id=c.id,
        detail=c.name,
        request=request,
    )
    return jsonify(serialize_class(c)), 200


@sessions_admin_bp.route("/classes/<class_id>", methods=["DELETE"])
@admin_required
def delete_class(class_id):
    c = Class.query.get(class_id)
    if not c:
        return _error("Class not found.", "not_found", 404)
    c.is_active = False
    db.session.commit()
    log_action(
        "class_deactivated",
        user_id=get_jwt_identity(),
        resource_type="class",
        resource_id=c.id,
        detail=c.name,
        request=request,
    )
    return jsonify({"deactivated": True}), 200


@sessions_admin_bp.route("/sessions/upload-image", methods=["POST"])
@admin_required
def upload_session_image():
    if "file" not in request.files:
        return _error("No file was uploaded.", "missing_file", 400)

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return _error("No file selected.", "empty_file", 400)

    original_filename = secure_filename(uploaded_file.filename) or "event.png"
    ext = os.path.splitext(original_filename)[1].lower()

    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return _error("Only PNG, JPG, WEBP, and GIF images are allowed.", "invalid_file_type", 400)

    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > 5 * 1024 * 1024:
        return _error("Image size exceeds 5MB limit.", "file_too_large", 400)

    import cloudinary.uploader
    try:
        result = cloudinary.uploader.upload(
            uploaded_file,
            folder="session_images",
            public_id=f"{uuid.uuid4().hex}_{original_filename.split('.')[0]}"
        )
        url = result.get("secure_url")
        log_action(
            "session_image_uploaded",
            user_id=get_jwt_identity(),
            resource_type="session_image",
            detail=original_filename,
            request=request,
        )
        return jsonify({"url": url, "filename": original_filename}), 200
    except Exception as e:
        return _error(f"Cloudinary upload failed: {str(e)}", "upload_failed", 500)


# --- Sessions ---

@sessions_admin_bp.route("/sessions", methods=["GET"])
@admin_required
def list_sessions_admin():
    sessions = Session.query.order_by(Session.start_time.desc()).all()
    return jsonify([serialize_session(s, detail=True) for s in sessions]), 200


@sessions_admin_bp.route("/sessions", methods=["POST"])
@admin_required
def create_session():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    start_time = data.get("start_time")
    end_time = data.get("end_time")

    if not title:
        return _error("Session title is required.", "invalid_title", 400)
    if not start_time or not end_time:
        return _error("start_time and end_time are required.", "invalid_time", 400)

    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except ValueError:
        return _error("Times must be ISO 8601 format.", "invalid_time_format", 400)

    if end_dt <= start_dt:
        return _error("end_time must be after start_time.", "invalid_time_range", 400)

    s = Session(
        class_id=data.get("class_id"),
        title=title,
        description=data.get("description"),
        start_time=start_dt,
        end_time=end_dt,
        location=data.get("location", "Studio"),
        capacity=int(data.get("capacity", 12)),
        price=data.get("price"),
        status="scheduled",
        image_url=data.get("image_url"),
    )
    db.session.add(s)
    db.session.commit()
    log_action(
        "session_created",
        user_id=get_jwt_identity(),
        resource_type="session",
        resource_id=s.id,
        detail=s.title,
        request=request,
    )
    return jsonify({"id": s.id, "title": s.title}), 201


@sessions_admin_bp.route("/sessions/<session_id>", methods=["PATCH"])
@admin_required
def update_session(session_id):
    s = Session.query.get(session_id)
    if not s:
        return _error("Session not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return _error("Title cannot be empty.", "invalid_title", 400)
        s.title = title
    if "description" in data:
        s.description = data.get("description")
    if "location" in data:
        s.location = data.get("location")
    if "capacity" in data:
        new_capacity = int(data.get("capacity"))
        if new_capacity < s.confirmed_booking_count:
            return _error(
                f"Capacity can't be set below the current {s.confirmed_booking_count} confirmed bookings.",
                "capacity_below_bookings",
                400,
            )
        s.capacity = new_capacity
    if "price" in data:
        s.price = data.get("price")
    if "image_url" in data:
        s.image_url = data.get("image_url")

    db.session.commit()
    log_action(
        "session_updated",
        user_id=get_jwt_identity(),
        resource_type="session",
        resource_id=s.id,
        detail=s.title,
        request=request,
    )
    return jsonify(serialize_session(s, detail=True)), 200


@sessions_admin_bp.route("/sessions/<session_id>/cancel", methods=["PATCH"])
@admin_required
def cancel_session(session_id):
    from services.email_service import send_cancellation_notice

    s = Session.query.get(session_id)
    if not s:
        return _error("Session not found.", "not_found", 404)

    s.status = "cancelled"
    affected = []
    for booking in s.bookings.filter_by(status="confirmed").all():
        booking.status = "cancelled"
        affected.append(booking.contact_email())
        send_cancellation_notice(booking)

    db.session.commit()

    log_action(
        "session_cancelled",
        user_id=get_jwt_identity(),
        resource_type="session",
        resource_id=s.id,
        detail=f"bookings_notified={len(affected)}",
        request=request,
    )

    return jsonify({"cancelled": True, "notified": affected}), 200
