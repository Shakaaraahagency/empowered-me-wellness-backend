from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class AuditLog(db.Model):
    """Append-only record of security-relevant events: logins, admin
    actions, and cancellations. Never updated or deleted by application
    code — only ever inserted. user_id is nullable because some events
    (e.g. a failed login with a bad email) happen before we know who the
    actor is, or the actor is a guest."""

    __tablename__ = "audit_log"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    user_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=True, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(50), nullable=True)
    resource_id = db.Column(db.String(64), nullable=True)
    detail = db.Column(db.String(500), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), index=True
    )

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "detail": self.detail,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
