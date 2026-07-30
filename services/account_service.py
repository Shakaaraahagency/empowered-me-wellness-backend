import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from extensions import db
from models.user import User, TokenBlocklist
from models.password_reset_token import PasswordResetToken

logger = logging.getLogger("emw")

RESET_TOKEN_EXPIRY_MINUTES = 30


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def request_password_reset(email: str) -> None:
    """
    Always succeeds from the caller's point of view, whether or not the
    email exists — the route never reveals which. If it does exist, a
    single-use, 30-minute token is created and the reset link is logged
    server-side as a stand-in for real email delivery (Phase 6 replaces
    this log line with an actual sent email; nothing else about this
    function changes when that ships).
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        return

    raw_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES),
    )
    db.session.add(reset)
    db.session.commit()

    from services.email_service import send_password_reset
    from flask import current_app

    reset_link = f"{current_app.config['FRONTEND_BASE_URL']}/reset-password.html?token={raw_token}"
    send_password_reset(user.email, reset_link)


class ResetError(Exception):
    def __init__(self, message: str, code: str):
        self.message = message
        self.code = code
        super().__init__(message)


def reset_password(raw_token: str, new_password: str) -> None:
    token_hash = _hash_token(raw_token)
    reset = (
        PasswordResetToken.query.filter_by(token_hash=token_hash)
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )

    if not reset or not reset.is_valid:
        raise ResetError("This reset link is invalid or has expired.", "invalid_token")

    user = User.query.get(reset.user_id)
    if not user:
        raise ResetError("This reset link is invalid or has expired.", "invalid_token")

    user.set_password(new_password)
    reset.used_at = datetime.now(timezone.utc)

    # Changing the password invalidates every existing session — a stolen
    # session shouldn't survive a password reset.
    TokenBlocklist.query.filter_by(user_id=user.id, revoked=False).update({"revoked": True})

    db.session.commit()


def anonymize_account(user: User) -> None:
    """
    'Delete my account' scrubs personal identifying data but keeps the
    user row and every booking/order tied to it — Latoya's attendance and
    revenue records shouldn't break because a client exercised their
    PIPA-style right to have their personal data removed. This is the
    standard compliant pattern where there's a legitimate record-keeping
    need: anonymize, don't hard-delete, and say so plainly to the user.
    """
    anon_id = secrets.token_hex(8)
    user.email = f"deleted-user-{anon_id}@deleted.local"
    user.full_name = "Deleted User"
    user.phone = None
    user.email_verified = False
    # Overwrite the password hash with something nobody could ever supply —
    # this account can never be logged into again, by anyone.
    user.set_password(secrets.token_urlsafe(48))

    TokenBlocklist.query.filter_by(user_id=user.id, revoked=False).update({"revoked": True})

    db.session.commit()
