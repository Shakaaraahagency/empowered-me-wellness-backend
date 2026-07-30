import re
from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(280), nullable=False, unique=True, index=True)
    excerpt = db.Column(db.Text, nullable=True)
    content = db.Column(db.Text, nullable=False)
    cover_image_url = db.Column(db.String(500), nullable=True)
    author_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=True)

    status = db.Column(db.String(20), nullable=False, default="draft")  # draft / published
    seo_title = db.Column(db.String(255), nullable=True)
    seo_description = db.Column(db.String(500), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    published_at = db.Column(db.DateTime, nullable=True)


from models.user import User  # noqa: E402

BlogPost.author = db.relationship("User")
