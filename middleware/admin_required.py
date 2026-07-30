from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("role") != "admin":
            return _error("Admin access required.", "forbidden", 403)
        return fn(*args, **kwargs)

    return wrapper
