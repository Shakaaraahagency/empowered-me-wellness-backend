from flask import Blueprint, jsonify, request

from extensions import db
from models.product_review import ProductReview
from models.product import Product
from middleware.admin_required import admin_required

reviews_admin_bp = Blueprint("reviews_admin", __name__, url_prefix="/api/v1/admin/reviews")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _serialize_admin(r):
    return {
        "id": r.id,
        "product_id": r.product_id,
        "product_name": r.product.name if r.product else "Unknown Product",
        "author_name": r.author_name,
        "rating": r.rating,
        "content": r.content,
        "is_approved": r.is_approved,
        "created_at": r.created_at.isoformat(),
    }


@reviews_admin_bp.route("", methods=["GET"])
@admin_required
def list_reviews_admin():
    reviews = ProductReview.query.order_by(ProductReview.created_at.desc()).all()
    return jsonify([_serialize_admin(r) for r in reviews]), 200


@reviews_admin_bp.route("/<review_id>", methods=["PATCH"])
@admin_required
def update_review(review_id):
    r = ProductReview.query.get(review_id)
    if not r:
        return _error("Review not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    if "is_approved" in data:
        r.is_approved = bool(data.get("is_approved"))

    db.session.commit()
    return jsonify(_serialize_admin(r)), 200


@reviews_admin_bp.route("/<review_id>", methods=["DELETE"])
@admin_required
def delete_review(review_id):
    r = ProductReview.query.get(review_id)
    if not r:
        return _error("Review not found.", "not_found", 404)
    db.session.delete(r)
    db.session.commit()
    return jsonify({"deleted": True}), 200
