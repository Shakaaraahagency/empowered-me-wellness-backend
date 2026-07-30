from flask import Blueprint, jsonify

from extensions import db
from models.class_ import Class, Session
from serializers.session_serializer import serialize_class, serialize_session

sessions_bp = Blueprint("sessions", __name__, url_prefix="/api/v1")


@sessions_bp.route("/classes", methods=["GET"])
def list_classes():
    classes = Class.query.filter_by(is_active=True).all()
    return jsonify([serialize_class(c) for c in classes]), 200


@sessions_bp.route("/sessions", methods=["GET"])
def list_sessions():
    sessions = (
        Session.query.filter_by(status="scheduled")
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
    session = Session.query.get(session_id)
    if not session:
        return jsonify({"error": {"message": "Session not found.", "code": "not_found"}}), 404
    return jsonify(serialize_session(session, detail=True)), 200
