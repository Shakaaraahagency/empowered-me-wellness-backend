import re
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from extensions import db, limiter
from models.user import User, TokenBlocklist
from services.account_service import (
    request_password_reset,
    reset_password,
    ResetError,
    anonymize_account,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


def _record_token(jwt_payload, user_id):
    """Store every issued token's jti so logout can revoke it for real."""
    expires = datetime.fromtimestamp(jwt_payload["exp"], tz=timezone.utc)
    db.session.add(
        TokenBlocklist(
            jti=jwt_payload["jti"],
            token_type=jwt_payload["type"],
            user_id=user_id,
            revoked=False,
            expires_at=expires,
        )
    )


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

    # --- backend validation — never trust the frontend to have checked this ---
    if not email or not EMAIL_RE.match(email):
        return _error("Please provide a valid email address.", "invalid_email", 400)
    if len(password) < 8:
        return _error("Password must be at least 8 characters.", "weak_password", 400)
    if not full_name or len(full_name) > 255:
        return _error("Please provide your name.", "invalid_name", 400)

    if User.query.filter_by(email=email).first():
        # Same message whether the account exists or the password was ever
        # wrong later at login — we don't confirm which emails are registered.
        return _error(
            "Could not create account with those details.", "registration_failed", 400
        )

    user = User(email=email, full_name=full_name, phone=(data.get("phone") or None))
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"id": user.id, "email": user.email, "full_name": user.full_name}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    from flask import current_app
    env_admin_email = current_app.config.get("ADMIN_EMAIL")
    env_admin_pass = current_app.config.get("ADMIN_PASSWORD")

    user = None

    # Auto-provision or update env-based admin on login
    if env_admin_email and env_admin_pass and email == env_admin_email.strip().lower() and password == env_admin_pass:
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, full_name="System Admin", role="admin")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        else:
            # If they exist but the password/role is out of sync with env, force sync it
            if user.role != "admin" or not user.check_password(password):
                user.role = "admin"
                user.set_password(password)
                db.session.commit()
    else:
        # Standard login flow
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return _error("Invalid email or password.", "invalid_credentials", 401)

    access_token = create_access_token(identity=user.id, additional_claims={"role": user.role})
    refresh_token = create_refresh_token(identity=user.id)

    from flask_jwt_extended import get_csrf_token
    resp = jsonify({
        "id": user.id, 
        "email": user.email, 
        "full_name": user.full_name,
        "csrf_access": get_csrf_token(access_token),
        "csrf_refresh": get_csrf_token(refresh_token)
    })
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)

    from flask_jwt_extended import decode_token

    _record_token(decode_token(access_token), user.id)
    _record_token(decode_token(refresh_token), user.id)
    db.session.commit()

    return resp, 200


@auth_bp.route("/refresh", methods=["POST"])
@limiter.limit("20 per minute")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user:
        return _error("Account not found.", "not_found", 404)

    new_access = create_access_token(identity=user.id, additional_claims={"role": user.role})
    
    from flask_jwt_extended import get_csrf_token
    resp = jsonify({
        "refreshed": True,
        "csrf_access": get_csrf_token(new_access)
    })
    set_access_cookies(resp, new_access)

    from flask_jwt_extended import decode_token

    _record_token(decode_token(new_access), user.id)
    db.session.commit()

    return resp, 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(optional=True, verify_type=False)
def logout():
    """
    Revokes the *current* token's jti server-side (whichever cookie was
    presented) and clears cookies. Unsets cookies and succeeds even if the
    token is expired or missing.
    """
    jwt_payload = get_jwt() or {}
    jti = jwt_payload.get("jti")
    if jti:
        entry = TokenBlocklist.query.filter_by(jti=jti).first()
        if entry:
            entry.revoked = True
            db.session.commit()

    resp = jsonify({"logged_out": True})
    unset_jwt_cookies(resp)
    return resp, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user:
        return _error("Account not found.", "not_found", 404)
    return jsonify(
        {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        }
    ), 200


# --- Password reset ---

@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("3 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()

    if email and EMAIL_RE.match(email):
        request_password_reset(email)

    # Same response whether the email exists or not — never confirm which.
    return jsonify(
        {"message": "If an account exists for that email, a reset link has been sent."}
    ), 200


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("5 per hour")
def reset_password_route():
    data = request.get_json(silent=True) or {}
    token = data.get("token") or ""
    new_password = data.get("password") or ""

    if not token:
        return _error("Reset token is required.", "missing_token", 400)
    if len(new_password) < 8:
        return _error("Password must be at least 8 characters.", "weak_password", 400)

    try:
        reset_password(token, new_password)
    except ResetError as e:
        return _error(e.message, e.code, 400)

    return jsonify({"message": "Password updated. Please log in with your new password."}), 200


# --- Profile management ---

@auth_bp.route("/me", methods=["PATCH"])
@jwt_required()
def update_me():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user:
        return _error("Account not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}

    if "full_name" in data:
        full_name = (data.get("full_name") or "").strip()
        if not full_name or len(full_name) > 255:
            return _error("Please provide a valid name.", "invalid_name", 400)
        user.full_name = full_name

    if "phone" in data:
        phone = (data.get("phone") or "").strip()
        user.phone = phone or None

    db.session.commit()

    return jsonify(
        {"id": user.id, "email": user.email, "full_name": user.full_name, "phone": user.phone}
    ), 200


@auth_bp.route("/me", methods=["DELETE"])
@jwt_required()
def delete_me():
    identity = get_jwt_identity()
    user = User.query.get(identity)
    if not user:
        return _error("Account not found.", "not_found", 404)

    anonymize_account(user)

    resp = jsonify(
        {
            "deleted": True,
            "message": "Your account has been deleted. Booking and order history is retained "
            "in anonymized form for business record-keeping, with your personal details removed.",
        }
    )
    unset_jwt_cookies(resp)
    return resp, 200
