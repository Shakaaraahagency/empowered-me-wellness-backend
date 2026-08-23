import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from werkzeug.utils import secure_filename

from extensions import db
from models.blog_post import BlogPost, slugify
from serializers.blog_serializer import serialize_post_admin
from services.audit_service import log_action
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


@blog_admin_bp.route("/upload-media", methods=["POST"])
@admin_required
def upload_blog_media():
    """Upload an image or short video clip for use in blog posts."""
    if "file" not in request.files:
        return _error("No file was uploaded.", "missing_file", 400)

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return _error("No file selected.", "empty_file", 400)

    original_filename = secure_filename(uploaded_file.filename) or "media.png"
    ext = os.path.splitext(original_filename)[1].lower()

    IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    VIDEO_EXTS = {".mp4", ".webm", ".mov"}

    if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
        return _error(
            "Only PNG, JPG, WEBP, GIF images and MP4, WEBM, MOV videos are allowed.",
            "invalid_file_type", 400,
        )

    is_video = ext in VIDEO_EXTS
    max_size = 50 * 1024 * 1024 if is_video else 5 * 1024 * 1024

    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > max_size:
        limit_label = "50MB" if is_video else "5MB"
        return _error(f"File size exceeds {limit_label} limit.", "file_too_large", 400)

    import cloudinary.uploader
    try:
        upload_kwargs = {
            "folder": "blog_media",
            "public_id": f"{uuid.uuid4().hex}_{original_filename.split('.')[0]}",
        }
        if is_video:
            upload_kwargs["resource_type"] = "video"

        result = cloudinary.uploader.upload(uploaded_file, **upload_kwargs)
        url = result.get("secure_url")
        media_type = "video" if is_video else "image"
        log_action(
            "blog_media_uploaded",
            user_id=get_jwt_identity(),
            resource_type="blog_media",
            detail=f"{original_filename} ({media_type})",
            request=request,
        )
        return jsonify({"url": url, "filename": original_filename, "type": media_type}), 200
    except Exception as e:
        return _error(f"Cloudinary upload failed: {str(e)}", "upload_failed", 500)


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
    log_action(
        "blog_post_created",
        user_id=author_id,
        resource_type="blog_post",
        resource_id=post.id,
        detail=post.title,
        request=request,
    )
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

    was_published = post.status == "published"
    if "status" in data:
        new_status = data.get("status")
        if new_status not in ("draft", "published"):
            return _error("status must be 'draft' or 'published'.", "invalid_status", 400)
        if new_status == "published" and post.status != "published":
            post.published_at = datetime.now(timezone.utc)
        post.status = new_status

    db.session.commit()

    action = "blog_post_published" if (not was_published and post.status == "published") else "blog_post_updated"
    log_action(
        action,
        user_id=get_jwt_identity(),
        resource_type="blog_post",
        resource_id=post.id,
        detail=post.title,
        request=request,
    )

    return jsonify(serialize_post_admin(post)), 200


@blog_admin_bp.route("/<post_id>", methods=["DELETE"])
@admin_required
def delete_post(post_id):
    post = BlogPost.query.get(post_id)
    if not post:
        return _error("Post not found.", "not_found", 404)
    title = post.title
    db.session.delete(post)
    db.session.commit()
    log_action(
        "blog_post_deleted",
        user_id=get_jwt_identity(),
        resource_type="blog_post",
        resource_id=post_id,
        detail=title,
        request=request,
    )
    return jsonify({"deleted": True}), 200
