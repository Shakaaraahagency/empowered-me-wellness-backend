from flask import current_app

from extensions import db
from models.audit_log import AuditLog


def _client_ip(request) -> str | None:
    if request is None:
        return None
    # Render sits behind a proxy; the real client IP is the first entry
    # in X-Forwarded-For when present.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def log_action(
    action: str,
    user_id: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
    request=None,
) -> None:
    """Write one append-only audit log row.

    This never raises — a failure to write the audit log should never
    break the actual user-facing action it's logging. Failures are
    logged server-side instead so they're still visible to us.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            detail=detail[:500] if detail else None,
            ip_address=_client_ip(request),
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Failed to write audit log entry for action=%s", action)
