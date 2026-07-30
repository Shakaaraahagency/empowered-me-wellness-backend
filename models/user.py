from datetime import datetime, timezone

import bcrypt

from extensions import db
from models.types import GUID, new_uuid


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(GUID(), primary_key=True, default=new_uuid)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    role = db.Column(db.String(20), nullable=False, default="visitor_account")
    email_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def set_password(self, plain_password: str) -> None:
        self.password_hash = bcrypt.hashpw(
            plain_password.encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

    def check_password(self, plain_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), self.password_hash.encode("utf-8")
        )

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class TokenBlocklist(db.Model):
    """
    Every JWT's unique id (jti) gets recorded here when a refresh token is
    issued. On logout, the jti is marked revoked. This is what makes logout
    a real server-side invalidation instead of just deleting a cookie in
    the browser — a token stolen before logout can't be replayed after it.
    """

    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True, unique=True)
    token_type = db.Column(db.String(10), nullable=False)  # "access" or "refresh"
    user_id = db.Column(GUID(), db.ForeignKey("users.id"), nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
