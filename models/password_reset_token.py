from datetime import datetime, timezone

from extensions import db
from models.types import GUID, new_uuid


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    user_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=False)

    # We store a hash of the token, never the raw value — same principle as
    # a password. If the DB leaked, stored hashes alone can't reset anyone's
    # account; you still need the raw token that was only ever shown once.
    token_hash = db.Column(db.String(64), nullable=False, index=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)

    @property
    def is_valid(self) -> bool:
        if self.used_at is not None:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < expires
