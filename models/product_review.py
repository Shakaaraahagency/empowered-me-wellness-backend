from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class ProductReview(db.Model):
    __tablename__ = "product_reviews"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    product_id = db.Column(GUID(), db.ForeignKey("products.id"), nullable=False)
    author_name = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Integer, nullable=False, default=5)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to Product
    product = db.relationship("Product", backref=db.backref("reviews", lazy="dynamic", cascade="all, delete-orphan"))
