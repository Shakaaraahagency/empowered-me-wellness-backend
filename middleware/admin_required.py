import logging
from functools import wraps

from flask import jsonify, request as flask_request
from flask_jwt_extended import verify_jwt_in_request, get_jwt


logger = logging.getLogger("emw.auth")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except Exception as exc:
            logger.warning(
                "JWT verification failed: %s: %s | method=%s path=%s csrf_header=%s",
                type(exc).__name__,
                exc,
                flask_request.method,
                flask_request.path,
                flask_request.headers.get("X-CSRF-TOKEN", "<missing>"),
            )
            raise
        claims = get_jwt()
        if claims.get("role") != "admin":
            return _error("Admin access required.", "forbidden", 403)
        return fn(*args, **kwargs)

    return wrapper

