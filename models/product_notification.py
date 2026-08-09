from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class ProductNotification(db.Model):
    """Tracks 'Notify Me' sign-ups for coming-soon products.

    Separate from NewsletterSubscriber so that:
    - One email can subscribe to multiple coming-soon products.
    - Newsletter unsubscribe doesn't affect product notifications.
    - The admin can see exactly who is waiting for each product.
    """
    __tablename__ = "product_notifications"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    product_id = db.Column(GUID(), db.ForeignKey("products.id"), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Prevent duplicate sign-ups for the same product
    __table_args__ = (
        db.UniqueConstraint("product_id", "email", name="uq_product_notification_email"),
    )

    product = db.relationship("Product", backref=db.backref("notifications", lazy="dynamic"))
