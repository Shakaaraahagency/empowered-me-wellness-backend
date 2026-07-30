import csv
import io

from flask import Blueprint, jsonify, request, Response

from models.newsletter import NewsletterSubscriber
from middleware.admin_required import admin_required

subscribers_admin_bp = Blueprint(
    "subscribers_admin", __name__, url_prefix="/api/v1/admin/subscribers"
)


def _serialize(s):
    return {
        "id": s.id,
        "email": s.email,
        "status": s.status,
        "subscribed_at": s.subscribed_at.isoformat(),
    }


@subscribers_admin_bp.route("", methods=["GET"])
@admin_required
def list_subscribers():
    status_filter = request.args.get("status", "active")
    query = NewsletterSubscriber.query
    if status_filter != "all":
        query = query.filter_by(status=status_filter)
    subs = query.order_by(NewsletterSubscriber.subscribed_at.desc()).all()
    return jsonify([_serialize(s) for s in subs]), 200


@subscribers_admin_bp.route("/export", methods=["GET"])
@admin_required
def export_subscribers():
    subs = NewsletterSubscriber.query.filter_by(status="active").order_by(
        NewsletterSubscriber.subscribed_at
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["email", "subscribed_at"])
    for s in subs:
        writer.writerow([s.email, s.subscribed_at.isoformat()])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=newsletter-subscribers.csv"},
    )
