from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def ownership_required(loader_fn):
    """
    Usage:
        @ownership_required(lambda booking_id: Booking.query.get(booking_id))
        def get_booking(booking_id):
            ...

    Confirms the resource's user_id matches the requester's identity, OR the
    requester is an admin. Loads the resource once here so the route doesn't
    have to re-query and re-check by hand — this is the one place an
    ownership bug can be fixed instead of six.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            identity = get_jwt_identity()
            claims = get_jwt()

            resource = loader_fn(*args, **kwargs)
            if resource is None:
                return _error("Not found.", "not_found", 404)

            is_owner = getattr(resource, "user_id", None) == identity
            is_admin = claims.get("role") == "admin"

            if not (is_owner or is_admin):
                return _error(
                    "You don't have permission to access this.", "forbidden", 403
                )

            return fn(*args, resource=resource, **kwargs)

        return wrapper

    return decorator
