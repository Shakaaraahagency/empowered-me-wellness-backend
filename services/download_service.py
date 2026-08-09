import os

from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


def _serializer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"], salt="product-download"
    )


def generate_download_token(order_id: str, product_id: str) -> str:
    """Signed token encoding which order+product this download is for.
    Expires after DOWNLOAD_LINK_EXPIRY_SECONDS — checked at verify time,
    not baked into the token itself, so the expiry window is configurable
    without reissuing tokens."""
    return _serializer().dumps({"order_id": order_id, "product_id": product_id})


def verify_download_token(token: str) -> dict:
    """Returns {'order_id', 'product_id'} or raises ValueError with a
    user-safe message — never leaks why exactly a token failed beyond
    'expired' vs 'invalid', which is enough for a legitimate user to
    understand without giving an attacker useful signal."""
    max_age = current_app.config["DOWNLOAD_LINK_EXPIRY_SECONDS"]
    try:
        return _serializer().loads(token, max_age=max_age)
    except SignatureExpired:
        raise ValueError("This download link has expired. Request a new one from your order history.")
    except BadSignature:
        raise ValueError("This download link is invalid.")


def resolve_file_path(relative_path: str) -> str:
    """Resolves a product's stored file_path against the protected files
    directory. Always contained within PROTECTED_FILES_DIR — there is no
    escape hatch for absolute paths, even ones that exist on disk, because
    admins can type this value into a plain text field and it should never
    be trusted to point anywhere outside the sandboxed directory."""
    if not relative_path:
        raise ValueError("Empty file path.")

    clean_path = relative_path.strip(" '\"")

    base = os.path.abspath(current_app.config["PROTECTED_FILES_DIR"])
    full = os.path.abspath(os.path.join(base, clean_path))
    if not full.startswith(base + os.sep) and full != base:
        raise ValueError("Invalid file path.")
    return full
