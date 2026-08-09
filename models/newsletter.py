from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    source = db.Column(db.String(100), nullable=True, default='website')
    status = db.Column(db.String(20), nullable=False, default="active")  # active / unsubscribed
    subscribed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    unsubscribed_at = db.Column(db.DateTime, nullable=True)
