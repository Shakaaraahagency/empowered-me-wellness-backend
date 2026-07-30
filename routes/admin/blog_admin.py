from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from extensions import db
from models.blog_post import BlogPost, slugify
from serializers.blog_serializer import serialize_post_admin
from middleware.admin_required import admin_required

blog_admin_bp = Blueprint("blog_admin", __name__, url_prefix="/api/v1/admin/blog")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _unique_slug(title: str, exclude_id=None) -> str:
    base = slugify(title) or "post"
    slug = base
    n = 2
    while True:
        existing = BlogPost.query.filter_by(slug=slug).first()
        if not existing or existing.id == exclude_id:
            return slug
        slug = f"{base}-{n}"
        n += 1


@blog_admin_bp.route("", methods=["GET"])
@admin_required
def list_posts_admin():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return jsonify([serialize_post_admin(p) for p in posts]), 200


@blog_admin_bp.route("", methods=["POST"])
@admin_required
def create_post():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()

    if not title:
        return _error("Title is required.", "invalid_title", 400)
    if not content:
        return _error("Content is required.", "invalid_content", 400)

    verify_jwt_in_request()
    author_id = get_jwt_identity()

    post = BlogPost(
        title=title,
        slug=_unique_slug(title),
        excerpt=data.get("excerpt"),
        content=content,
        cover_image_url=data.get("cover_image_url"),
        author_id=author_id,
        status="draft",
        seo_title=data.get("seo_title"),
        seo_description=data.get("seo_description"),
    )
    db.session.add(post)
    db.session.commit()
    return jsonify(serialize_post_admin(post)), 201


@blog_admin_bp.route("/<post_id>", methods=["PATCH"])
@admin_required
def update_post(post_id):
    post = BlogPost.query.get(post_id)
    if not post:
        return _error("Post not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return _error("Title cannot be empty.", "invalid_title", 400)
        if title != post.title:
            post.slug = _unique_slug(title, exclude_id=post.id)
        post.title = title
    if "content" in data:
        content = (data.get("content") or "").strip()
        if not content:
            return _error("Content cannot be empty.", "invalid_content", 400)
        post.content = content
    if "excerpt" in data:
        post.excerpt = data.get("excerpt")
    if "cover_image_url" in data:
        post.cover_image_url = data.get("cover_image_url")
    if "seo_title" in data:
        post.seo_title = data.get("seo_title")
    if "seo_description" in data:
        post.seo_description = data.get("seo_description")

    if "status" in data:
        new_status = data.get("status")
        if new_status not in ("draft", "published"):
            return _error("status must be 'draft' or 'published'.", "invalid_status", 400)
        if new_status == "published" and post.status != "published":
            post.published_at = datetime.now(timezone.utc)
        post.status = new_status

    db.session.commit()
    return jsonify(serialize_post_admin(post)), 200


@blog_admin_bp.route("/<post_id>", methods=["DELETE"])
@admin_required
def delete_post(post_id):
    post = BlogPost.query.get(post_id)
    if not post:
        return _error("Post not found.", "not_found", 404)
    db.session.delete(post)
    db.session.commit()
    return jsonify({"deleted": True}), 200
