from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="new")  # new/read/replied
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
