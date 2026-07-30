from flask import Blueprint, jsonify

from middleware.admin_required import admin_required
from services.stats_service import get_overview_stats

stats_admin_bp = Blueprint("stats_admin", __name__, url_prefix="/api/v1/admin/stats")


@stats_admin_bp.route("", methods=["GET"])
@admin_required
def overview_stats():
    return jsonify(get_overview_stats()), 200
