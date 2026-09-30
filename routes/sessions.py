from flask import Blueprint, jsonify

from extensions import db
from models.class_ import Class, Session
from serializers.session_serializer import serialize_class, serialize_session

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/v1")


def close_past_sessions():
    """Lazily close any scheduled sessions whose end_time has passed.

    Called on every public or admin listing request so the database
    stays clean without needing a cron job or background worker.
    Uses db.func.now() so the comparison happens entirely inside
    PostgreSQL, avoiding Python timezone-aware vs naive mismatches.
    """
    count = (
        Session.query
        .filter(Session.status == "scheduled", Session.end_time < db.func.now())
        .update({"status": "closed"}, synchronize_session="fetch")
    )
    if count:
        db.session.commit()
    return count


@sessions_bp.route("/classes", methods=["GET"])
def list_classes():
    classes = Class.query.filter_by(is_active=True).all()
    return jsonify([serialize_class(c) for c in classes]), 200


@sessions_bp.route("/sessions", methods=["GET"])
def list_sessions():
    # Auto-close any sessions that have ended
    close_past_sessions()

    sessions = (
        Session.query.filter_by(status="scheduled")
        .filter(
            # Only show sessions that haven't ended yet
            Session.end_time > db.func.now()
        )
        .filter(
            # Either the session has no linked class (one-off event)
            # or its linked class is active
            (Session.class_id == None) | 
            Session.class_id.in_(
                db.session.query(Class.id).filter_by(is_active=True)
            )
        )
        .order_by(Session.start_time.asc())
        .all()
    )
    return jsonify([serialize_session(s) for s in sessions]), 200


@sessions_bp.route("/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    # Auto-close any sessions that have ended
    close_past_sessions()

    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": {"message": "Session not found.", "code": "not_found"}}), 404
    return jsonify(serialize_session(session, detail=True)), 200
