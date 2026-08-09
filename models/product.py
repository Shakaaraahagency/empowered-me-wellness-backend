from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.String(100), nullable=True, default="ebook")
    # Path relative to PROTECTED_FILES_DIR — never a publicly reachable URL.
    # The actual download URL is generated on demand via download_service.
    file_path = db.Column(db.String(500), nullable=True)
    cover_image_url = db.Column(db.String(500), nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_coming_soon = db.Column(db.Boolean, nullable=False, default=False)
    release_date = db.Column(db.String(50), nullable=True)  # Free-text like "Fall 2026", "January 2027"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
