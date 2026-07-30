from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    author_name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(255), nullable=True)  # e.g. "Parent of two"
    content = db.Column(db.Text, nullable=False)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
