from flask import Blueprint, jsonify, request

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
    return jsonify([serialize_order(o) for o in orders]), 200
