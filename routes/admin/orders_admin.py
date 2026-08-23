from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from models.order import Order
from serializers.order_serializer import serialize_order
from middleware.admin_required import admin_required

orders_admin_bp = Blueprint("orders_admin", __name__, url_prefix="/api/v1/admin/orders")


@orders_admin_bp.route("", methods=["GET"])
@admin_required
def list_orders_admin():
    status_filter = request.args.get("status")
    query = Order.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    orders = query.order_by(Order.created_at.desc()).limit(200).all()

    from services.payment_service import sync_order_payment_status
    for o in orders:
        if o.status == "pending":
            sync_order_payment_status(o)

    return jsonify([serialize_order(o) for o in orders]), 200


@orders_admin_bp.route("/cleanup-stale", methods=["POST"])
@admin_required
def cleanup_stale_orders_admin():
    """
    Manual trigger for the same stale-order cleanup the scheduled
    `flask cancel-stale-orders` cron job runs automatically. Lets an admin
    clear out abandoned-checkout clutter on demand from the dashboard
    without waiting for the next scheduled run, or as a fallback if the
    Render cron job isn't set up yet.
    """
    data = request.get_json(silent=True) or {}
    hours = data.get("older_than_hours", 24)
    try:
        hours = int(hours)
        if hours < 1:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": {"message": "older_than_hours must be a positive integer.", "code": "invalid_hours"}}), 400

    from services.payment_service import cancel_stale_pending_orders
    cancelled_ids = cancel_stale_pending_orders(older_than_hours=hours, triggered_by_user_id=get_jwt_identity())

    return jsonify({"cancelled_count": len(cancelled_ids), "cancelled_order_ids": cancelled_ids}), 200
