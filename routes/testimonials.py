from flask import Blueprint, jsonify

from models.testimonial import Testimonial

testimonials_bp = Blueprint("testimonials", __name__, url_prefix="/api/v1/testimonials")


def serialize_testimonial(t):
    return {
        "id": t.id,
        "author_name": t.author_name,
        "role": t.role,
        "content": t.content,
        "is_featured": t.is_featured,
    }


@testimonials_bp.route("", methods=["GET"])
def list_testimonials():
    testimonials = Testimonial.query.filter_by(is_approved=True).order_by(
        Testimonial.is_featured.desc(), Testimonial.created_at.desc()
    ).all()
    return jsonify([serialize_testimonial(t) for t in testimonials]), 200


@testimonials_bp.route("", methods=["POST"])
def submit_testimonial():
    from flask import request
    from extensions import db

    data = request.get_json(silent=True) or {}
    author_name = (data.get("author_name") or "").strip()
    role = (data.get("role") or "").strip()
    content = (data.get("content") or "").strip()

    if not author_name:
        return jsonify({"error": {"message": "Author name is required.", "code": "invalid_author"}}), 400
    if not content:
        return jsonify({"error": {"message": "Testimonial content is required.", "code": "invalid_content"}}), 400

    # Max lengths (enforce DB limits)
    if len(author_name) > 255: author_name = author_name[:255]
    if len(role) > 255: role = role[:255]

    t = Testimonial(
        author_name=author_name,
        role=role,
        content=content,
        is_featured=False,
        is_approved=False,  # Needs admin approval
    )
    db.session.add(t)
    db.session.commit()
    return jsonify({"success": True}), 201
