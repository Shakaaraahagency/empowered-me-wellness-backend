from flask import Blueprint, jsonify, request

from extensions import db
from models.testimonial import Testimonial
from middleware.admin_required import admin_required

testimonials_admin_bp = Blueprint(
    "testimonials_admin", __name__, url_prefix="/api/v1/admin/testimonials"
)


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _serialize_admin(t):
    return {
        "id": t.id,
        "author_name": t.author_name,
        "role": t.role,
        "content": t.content,
        "is_featured": t.is_featured,
        "is_approved": t.is_approved,
        "created_at": t.created_at.isoformat(),
    }


@testimonials_admin_bp.route("", methods=["GET"])
@admin_required
def list_testimonials_admin():
    testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
    return jsonify([_serialize_admin(t) for t in testimonials]), 200


@testimonials_admin_bp.route("", methods=["POST"])
@admin_required
def create_testimonial():
    data = request.get_json(silent=True) or {}
    author_name = (data.get("author_name") or "").strip()
    content = (data.get("content") or "").strip()

    if not author_name:
        return _error("Author name is required.", "invalid_author", 400)
    if not content:
        return _error("Content is required.", "invalid_content", 400)

    t = Testimonial(
        author_name=author_name,
        role=data.get("role"),
        content=content,
        is_featured=bool(data.get("is_featured", False)),
        is_approved=bool(data.get("is_approved", False)),
    )
    db.session.add(t)
    db.session.commit()
    return jsonify(_serialize_admin(t)), 201


@testimonials_admin_bp.route("/<testimonial_id>", methods=["PATCH"])
@admin_required
def update_testimonial(testimonial_id):
    t = Testimonial.query.get(testimonial_id)
    if not t:
        return _error("Testimonial not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    if "author_name" in data:
        t.author_name = (data.get("author_name") or "").strip()
    if "role" in data:
        t.role = data.get("role")
    if "content" in data:
        t.content = (data.get("content") or "").strip()
    if "is_featured" in data:
        t.is_featured = bool(data.get("is_featured"))
    if "is_approved" in data:
        t.is_approved = bool(data.get("is_approved"))

    db.session.commit()
    return jsonify(_serialize_admin(t)), 200


@testimonials_admin_bp.route("/<testimonial_id>", methods=["DELETE"])
@admin_required
def delete_testimonial(testimonial_id):
    t = Testimonial.query.get(testimonial_id)
    if not t:
        return _error("Testimonial not found.", "not_found", 404)
    db.session.delete(t)
    db.session.commit()
    return jsonify({"deleted": True}), 200
