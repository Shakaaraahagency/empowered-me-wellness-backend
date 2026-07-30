from flask import Blueprint, jsonify

from models.blog_post import BlogPost
from serializers.blog_serializer import serialize_post

blog_bp = Blueprint("blog", __name__, url_prefix="/api/v1/blog")


@blog_bp.route("", methods=["GET"])
def list_posts():
    posts = (
        BlogPost.query.filter_by(status="published")
        .order_by(BlogPost.published_at.desc())
        .all()
    )
    return jsonify([serialize_post(p) for p in posts]), 200


@blog_bp.route("/<slug>", methods=["GET"])
def get_post(slug):
    post = BlogPost.query.filter_by(slug=slug, status="published").first()
    if not post:
        return jsonify({"error": {"message": "Post not found.", "code": "not_found"}}), 404
    return jsonify(serialize_post(post, detail=True)), 200
