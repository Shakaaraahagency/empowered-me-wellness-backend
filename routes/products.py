from flask import Blueprint, jsonify

from models.product import Product
from serializers.product_serializer import serialize_product

products_bp = Blueprint("products", __name__, url_prefix="/api/v1/products")


@products_bp.route("", methods=["GET"])
def list_products():
    products = Product.query.filter_by(is_active=True).all()
    return jsonify([serialize_product(p) for p in products]), 200


@products_bp.route("/<product_id>", methods=["GET"])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product or not product.is_active:
        return jsonify({"error": {"message": "Product not found.", "code": "not_found"}}), 404
    return jsonify(serialize_product(product, detail=True)), 200


@products_bp.route("/<product_id>/reviews", methods=["GET"])
def list_product_reviews(product_id):
    from models.product_review import ProductReview
    product = Product.query.get(product_id)
    if not product or not product.is_active:
        return jsonify({"error": {"message": "Product not found.", "code": "not_found"}}), 404

    reviews = ProductReview.query.filter_by(product_id=product_id, is_approved=True).order_by(ProductReview.created_at.desc()).all()
    
    return jsonify([{
        "id": r.id,
        "author_name": r.author_name,
        "rating": r.rating,
        "content": r.content,
        "created_at": r.created_at.isoformat(),
    } for r in reviews]), 200


@products_bp.route("/<product_id>/reviews", methods=["POST"])
def submit_product_review(product_id):
    from flask import request
    from extensions import db
    from models.product_review import ProductReview

    product = Product.query.get(product_id)
    if not product or not product.is_active:
        return jsonify({"error": {"message": "Product not found.", "code": "not_found"}}), 404

    data = request.get_json(silent=True) or {}
    author_name = (data.get("author_name") or "").strip()
    content = (data.get("content") or "").strip()
    rating = data.get("rating", 5)

    if not author_name:
        return jsonify({"error": {"message": "Author name is required.", "code": "invalid_author"}}), 400
    if not content:
        return jsonify({"error": {"message": "Review content is required.", "code": "invalid_content"}}), 400
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": {"message": "Rating must be an integer between 1 and 5.", "code": "invalid_rating"}}), 400

    if len(author_name) > 255: author_name = author_name[:255]

    review = ProductReview(
        product_id=product.id,
        author_name=author_name,
        rating=rating,
        content=content,
        is_approved=False,
    )
    db.session.add(review)
    db.session.commit()
    
    return jsonify({"success": True}), 201
