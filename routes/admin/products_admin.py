import os
import uuid
from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename

from extensions import db
from models.product import Product
from serializers.product_serializer import serialize_product
from middleware.admin_required import admin_required

products_admin_bp = Blueprint("products_admin", __name__, url_prefix="/api/v1/admin/products")

ALLOWED_EXTENSIONS = {".pdf", ".epub", ".mobi"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _error(message: str, code: str, status: int):
    return jsonify({"error": {"message": message, "code": code}}), status


@products_admin_bp.route("/upload", methods=["POST"])
@admin_required
def upload_product_file():
    if "file" not in request.files:
        return _error("No file was uploaded.", "missing_file", 400)

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return _error("No file selected.", "empty_file", 400)

    original_filename = secure_filename(uploaded_file.filename) or "ebook.pdf"
    ext = os.path.splitext(original_filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        return _error("Only PDF, EPUB, and MOBI files are allowed.", "invalid_file_type", 400)

    # Check magic bytes for PDF
    header = uploaded_file.read(4)
    uploaded_file.seek(0)
    if ext == ".pdf" and not header.startswith(b"%PDF"):
        return _error("Invalid PDF file content.", "invalid_pdf", 400)

    # Check file size
    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > MAX_FILE_SIZE:
        return _error("File size exceeds 50MB limit.", "file_too_large", 400)

    import cloudinary.uploader
    try:
        result = cloudinary.uploader.upload(
            uploaded_file,
            folder="protected_books",
            resource_type="raw",
            type="authenticated",
            public_id=f"{uuid.uuid4().hex}_{original_filename}"
        )
        file_path = result.get("public_id")
        return jsonify({"file_path": file_path, "filename": original_filename}), 200
    except Exception as e:
        return _error(f"Cloudinary upload failed: {str(e)}", "upload_failed", 500)


@products_admin_bp.route("/upload-cover", methods=["POST"])
@admin_required
def upload_product_cover():
    if "file" not in request.files:
        return _error("No file was uploaded.", "missing_file", 400)

    uploaded_file = request.files["file"]
    if not uploaded_file or not uploaded_file.filename:
        return _error("No file selected.", "empty_file", 400)

    original_filename = secure_filename(uploaded_file.filename) or "cover.png"
    ext = os.path.splitext(original_filename)[1].lower()

    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return _error("Only PNG, JPG, WEBP, and GIF images are allowed.", "invalid_file_type", 400)

    # Check file size (5MB limit for images)
    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)
    if size > 5 * 1024 * 1024:
        return _error("Image size exceeds 5MB limit.", "file_too_large", 400)

    import cloudinary.uploader
    try:
        # We don't specify resource_type="raw" here because images should be treated as images
        result = cloudinary.uploader.upload(
            uploaded_file, 
            folder="covers",
            public_id=f"{uuid.uuid4().hex}_{original_filename.split('.')[0]}"
        )
        url = result.get("secure_url")
        return jsonify({"url": url, "filename": original_filename}), 200
    except Exception as e:
        return _error(f"Cloudinary upload failed: {str(e)}", "upload_failed", 500)


@products_admin_bp.route("", methods=["GET"])
@admin_required
def list_products_admin():
    products = Product.query.order_by(Product.name).all()
    return jsonify([serialize_product(p, detail=True) for p in products]), 200


@products_admin_bp.route("", methods=["POST"])
@admin_required
def create_product():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    price = data.get("price")
    file_path = (data.get("file_path") or "").strip(" '\"")
    is_coming_soon = bool(data.get("is_coming_soon", False))
    release_date = data.get("release_date")

    if not name:
        return _error("Product name is required.", "invalid_name", 400)
    if price is None or float(price) < 0:
        return _error("A valid price is required.", "invalid_price", 400)
        
    if is_coming_soon:
        file_path = file_path or None
    elif not file_path:
        return _error("file_path is required.", "invalid_file_path", 400)

    p = Product(
        name=name,
        description=data.get("description"),
        price=price,
        category=data.get("category", "ebook"),
        file_path=file_path,
        cover_image_url=data.get("cover_image_url"),
        is_coming_soon=is_coming_soon,
        release_date=release_date,
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({"id": p.id, "name": p.name}), 201


@products_admin_bp.route("/<product_id>", methods=["PATCH"])
@admin_required
def update_product(product_id):
    p = Product.query.get(product_id)
    if not p:
        return _error("Product not found.", "not_found", 404)

    data = request.get_json(silent=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return _error("Name cannot be empty.", "invalid_name", 400)
        p.name = name
    if "description" in data:
        p.description = data.get("description")
    if "price" in data:
        if float(data.get("price")) < 0:
            return _error("Price must be non-negative.", "invalid_price", 400)
        p.price = data.get("price")
    if "file_path" in data:
        p.file_path = (data.get("file_path") or "").strip(" '\"")
    if "cover_image_url" in data:
        p.cover_image_url = data.get("cover_image_url")
    if "is_active" in data:
        p.is_active = bool(data.get("is_active"))
    if "category" in data:
        p.category = data.get("category")
    if "release_date" in data:
        p.release_date = data.get("release_date")
    if "is_coming_soon" in data:
        new_is_coming_soon = bool(data.get("is_coming_soon"))
        if p.is_coming_soon and not new_is_coming_soon:
            # Switching from coming soon to live
            if not p.file_path and not ("file_path" in data and data.get("file_path")):
                return _error("Cannot switch from coming-soon to live without a product file. Upload the file first.", "missing_file", 400)
        p.is_coming_soon = new_is_coming_soon

    db.session.commit()
    return jsonify(serialize_product(p, detail=True)), 200


@products_admin_bp.route("/<product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    p = Product.query.get(product_id)
    if not p:
        return _error("Product not found.", "not_found", 404)
    # Soft delete — existing orders reference this product; hard-deleting
    # would break order history the same way hard-deleting a user would.
    p.is_active = False
    db.session.commit()
    return jsonify({"deactivated": True}), 200


@products_admin_bp.route("/<product_id>/release", methods=["POST"])
@admin_required
def release_product(product_id):
    """Release a coming-soon product: attach the file, flip is_coming_soon
    to False, and email every subscriber who signed up via 'Notify Me'."""
    from models.product_notification import ProductNotification
    from services.email_service import send_product_release_notification
    import logging

    logger = logging.getLogger("emw")

    p = Product.query.get(product_id)
    if not p:
        return _error("Product not found.", "not_found", 404)

    if not p.is_coming_soon:
        return _error("This product is already released.", "already_released", 400)

    # --- Accept file_path from JSON body (file was uploaded via /upload first) ---
    data = request.get_json(silent=True) or {}
    file_path = (data.get("file_path") or "").strip(" '\"")

    if not file_path:
        return _error(
            "A product file is required to release. Upload the file first via /upload.",
            "missing_file",
            400,
        )

    # Update the product
    p.file_path = file_path
    p.is_coming_soon = False
    db.session.commit()

    # --- Send notification emails to all subscribers ---
    subscribers = ProductNotification.query.filter_by(product_id=p.id).all()
    frontend_base = current_app.config.get("FRONTEND_BASE_URL", "http://127.0.0.1:5500")
    shop_url = f"{frontend_base}/product-detail.html?id={p.id}"

    sent_count = 0
    for sub in subscribers:
        try:
            send_product_release_notification(
                email=sub.email,
                product_name=p.name,
                shop_url=shop_url,
            )
            sent_count += 1
        except Exception:
            logger.exception("Failed to send release notification to %s", sub.email)

    # Clean up: remove the notification sign-ups since the product is live now
    ProductNotification.query.filter_by(product_id=p.id).delete()
    db.session.commit()

    return jsonify({
        "released": True,
        "product": serialize_product(p, detail=True),
        "notifications_sent": sent_count,
        "total_subscribers": len(subscribers),
    }), 200

