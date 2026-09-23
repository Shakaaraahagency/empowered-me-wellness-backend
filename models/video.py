import re
from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


def extract_youtube_id(url: str) -> str | None:
    """Extract the video ID from various YouTube URL formats."""
    if not url:
        return None
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    youtube_url = db.Column(db.String(500), nullable=False)
    youtube_id = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), nullable=False, default="general")
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft / published
    author_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    published_at = db.Column(db.DateTime, nullable=True)


from models.user import User  # noqa: E402

Video.author = db.relationship("User")
