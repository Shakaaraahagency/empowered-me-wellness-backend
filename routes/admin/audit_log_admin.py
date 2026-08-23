from flask import Blueprint, jsonify, request

from extensions import db
from models.audit_log import AuditLog
from models.user import User
from middleware.admin_required import admin_required

audit_log_admin_bp = Blueprint(
    "audit_log_admin", __name__, url_prefix="/api/v1/admin/audit-log"
)


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


@audit_log_admin_bp.route("", methods=["GET"])
@admin_required
def list_audit_log():
    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = min(max(int(request.args.get("per_page", 50)), 1), 200)
    except ValueError:
        return _error("page and per_page must be integers.", "invalid_pagination", 400)

    query = AuditLog.query

    action = request.args.get("action")
    if action:
        query = query.filter(AuditLog.action == action)

    date_from = request.args.get("from")
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)

    date_to = request.args.get("to")
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)

    total = query.count()
    entries = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    # One query to resolve every distinct user_id on this page to an email,
    # instead of N+1 queries — most pages will have far fewer distinct
    # users than rows, since the same admin tends to take several actions
    # in a row.
    user_ids = {e.user_id for e in entries if e.user_id}
    users_by_id = {}
    if user_ids:
        for u in User.query.filter(User.id.in_(user_ids)).all():
            users_by_id[str(u.id)] = {"email": u.email, "full_name": u.full_name}

    results = []
    for e in entries:
        row = e.to_dict()
        row["user"] = users_by_id.get(row["user_id"]) if row["user_id"] else None
        results.append(row)

    return jsonify(
        {
            "entries": results,
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    ), 200


@audit_log_admin_bp.route("/actions", methods=["GET"])
@admin_required
def list_distinct_actions():
    """Returns every distinct action string seen so far, for the filter
    dropdown — avoids hardcoding the list on the frontend as new action
    types get added over time."""
    rows = db.session.query(AuditLog.action).distinct().order_by(AuditLog.action).all()
    return jsonify({"actions": [r[0] for r in rows]}), 200
