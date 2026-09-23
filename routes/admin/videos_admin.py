from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from extensions import db
from models.video import Video, extract_youtube_id
from serializers.video_serializer import serialize_video_admin
from services.audit_service import log_action
from middleware.admin_required import admin_required

videos_admin_bp = Blueprint("videos_admin", __name__, url_prefix="/api/v1/admin/videos")

VALID_CATEGORIES = {"healing", "breathwork", "yoga", "mindfulness", "general"}


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


@videos_admin_bp.route("", methods=["GET"])
@admin_required
def list_videos_admin():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    return jsonify([serialize_video_admin(v) for v in videos]), 200


@videos_admin_bp.route("", methods=["POST"])
@admin_required
def create_video():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    youtube_url = (data.get("youtube_url") or "").strip()
    category = (data.get("category") or "general").strip().lower()

    if not title:
        return _error("Title is required.", "invalid_title", 400)
    if not youtube_url:
        return _error("YouTube URL is required.", "invalid_youtube_url", 400)

    youtube_id = extract_youtube_id(youtube_url)
    if not youtube_id:
        return _error(
            "Could not extract a valid YouTube video ID from the URL provided.",
            "invalid_youtube_url", 400,
        )

    if category not in VALID_CATEGORIES:
        return _error(
            f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}.",
            "invalid_category", 400,
        )

    verify_jwt_in_request()
    author_id = get_jwt_identity()

    video = Video(
        title=title,
        description=data.get("description"),
        youtube_url=youtube_url,
        youtube_id=youtube_id,
        category=category,
        author_id=author_id,
        status="draft",
    )
    db.session.add(video)
    db.session.commit()
    log_action(
        "video_created",
        user_id=author_id,
        resource_type="video",
        resource_id=video.id,
        detail=video.title,
        request=request,
    )
    return jsonify(serialize_video_admin(video)), 201


@videos_admin_bp.route("/<video_id>", methods=["PATCH"])
@admin_required
def update_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return _error("Video not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return _error("Title cannot be empty.", "invalid_title", 400)
        video.title = title

    if "description" in data:
        video.description = data.get("description")

    if "youtube_url" in data:
        youtube_url = (data.get("youtube_url") or "").strip()
        if not youtube_url:
            return _error("YouTube URL is required.", "invalid_youtube_url", 400)
        youtube_id = extract_youtube_id(youtube_url)
        if not youtube_id:
            return _error(
                "Could not extract a valid YouTube video ID from the URL provided.",
                "invalid_youtube_url", 400,
            )
        video.youtube_url = youtube_url
        video.youtube_id = youtube_id

    if "category" in data:
        category = (data.get("category") or "general").strip().lower()
        if category not in VALID_CATEGORIES:
            return _error(
                f"Category must be one of: {', '.join(sorted(VALID_CATEGORIES))}.",
                "invalid_category", 400,
            )
        video.category = category

    was_published = video.status == "published"
    if "status" in data:
        new_status = data.get("status")
        if new_status not in ("draft", "published"):
            return _error("status must be 'draft' or 'published'.", "invalid_status", 400)
        if new_status == "published" and video.status != "published":
            video.published_at = datetime.now(timezone.utc)
        video.status = new_status

    db.session.commit()

    action = "video_published" if (not was_published and video.status == "published") else "video_updated"
    log_action(
        action,
        user_id=get_jwt_identity(),
        resource_type="video",
        resource_id=video.id,
        detail=video.title,
        request=request,
    )
    return jsonify(serialize_video_admin(video)), 200


@videos_admin_bp.route("/<video_id>", methods=["DELETE"])
@admin_required
def delete_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return _error("Video not found.", "not_found", 404)
    title = video.title
    db.session.delete(video)
    db.session.commit()
    log_action(
        "video_deleted",
        user_id=get_jwt_identity(),
        resource_type="video",
        resource_id=video_id,
        detail=title,
        request=request,
    )
    return jsonify({"deleted": True}), 200
