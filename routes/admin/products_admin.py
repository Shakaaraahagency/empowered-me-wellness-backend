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

    if not name:
        return _error("Product name is required.", "invalid_name", 400)
    if price is None or float(price) < 0:
        return _error("A valid price is required.", "invalid_price", 400)
    if not file_path:
        return _error("file_path is required.", "invalid_file_path", 400)

    p = Product(
        name=name,
        description=data.get("description"),
        price=price,
        category=data.get("category", "ebook"),
        file_path=file_path,
        cover_image_url=data.get("cover_image_url"),
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
