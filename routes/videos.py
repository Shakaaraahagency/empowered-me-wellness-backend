from flask import Blueprint, jsonify, request

from models.video import Video
from serializers.video_serializer import serialize_video

videos_bp = Blueprint("videos", __name__, url_prefix="/api/v1/videos")


@videos_bp.route("", methods=["GET"])
def list_videos():
    query = Video.query.filter_by(status="published")

    category = request.args.get("category")
    if category:
        query = query.filter_by(category=category)

    videos = query.order_by(Video.published_at.desc()).all()
    return jsonify([serialize_video(v) for v in videos]), 200


@videos_bp.route("/<video_id>", methods=["GET"])
def get_video(video_id):
    video = Video.query.filter_by(id=video_id, status="published").first()
    if not video:
        return jsonify({"error": {"message": "Video not found.", "code": "not_found"}}), 404
    return jsonify(serialize_video(video)), 200
