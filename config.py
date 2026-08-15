import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env file automatically if present
load_dotenv()


class Config:
    """
    Every value here is read from the environment. Nothing sensitive is
    hardcoded. In production (Render) these are set as Environment Variables
    in the Render dashboard, never committed to the repo.
    """

    # --- Core Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    # --- Database ---
    # Render provides DATABASE_URL for its managed Postgres instances.
    # Render's URL sometimes starts with "postgres://" — SQLAlchemy 1.4+/2.x
    # requires "postgresql://", so we normalize it.
    _raw_db_url = os.environ.get("DATABASE_URL", "")
    if _raw_db_url.startswith("postgres://"):
        _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    from sqlalchemy import pool
    SQLALCHEMY_ENGINE_OPTIONS = {
        "poolclass": pool.NullPool,
        # Fail fast instead of hanging the whole request if the DB host is
        # unreachable (network partition, firewall block, DNS issue) — a
        # gunicorn worker stuck waiting on a dead TCP handshake for 60s+ can
        # take the whole app down under load. 10s is generous for a normal
        # connection and short enough to surface a real outage quickly.
        # SQLite's DBAPI doesn't accept connect_timeout at all (it's a
        # local file, there's no handshake to time out) — only apply this
        # for real network databases (MySQL/Postgres), so local dev
        # (which falls back to sqlite:// when DATABASE_URL isn't set,
        # see DevConfig below) isn't broken by it.
        **({} if _raw_db_url.startswith("sqlite") else {"connect_args": {"connect_timeout": 10}}),
    }
    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=20)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    # SameSite=None required for cross-origin cookies (Hostinger frontend → Render backend).
    # Browsers block SameSite=Lax cookies on cross-site fetch requests.
    # SameSite=None MUST be paired with Secure=True (HTTPS), which Render provides.
    JWT_COOKIE_SAMESITE = "None" if os.environ.get("FLASK_ENV") == "production" else "Lax"
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_PATH = "/api/v1/"
    JWT_REFRESH_COOKIE_PATH = "/api/v1/auth/refresh"

    # --- CORS ---
    # Comma-separated list of allowed origins, e.g.
    # "https://empoweredmewellness.com,https://www.empoweredmewellness.com"
    CORS_ORIGINS = [
        o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()
    ]

    # --- Rate limiting ---
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

    # --- Stripe ---
    # If unset, /checkout runs in a clearly-logged dev-only simulation mode
    # (see services/payment_service.py) rather than crashing. Production
    # deployments should set these for real before commerce goes live.
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
    STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY")

    # --- Downloads ---
    DOWNLOAD_LINK_EXPIRY_SECONDS = 60 * 60  # 1 hour
    PROTECTED_FILES_DIR = os.environ.get("PROTECTED_FILES_DIR", "protected_files")

    # --- Email (Resend) ---
    # If unset, all outbound email runs through a dev-only console-log
    # simulation instead (see services/email_service.py) — same pattern as
    # the Stripe dev fallback, and hard-disabled in production.
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
    EMAIL_FROM_ADDRESS = os.environ.get("EMAIL_FROM_ADDRESS", "no-reply@empoweredmewellness.com")
    # Used to build links inside emails (password reset, etc.) — the
    # frontend's real domain, not the API's.
    FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://127.0.0.1:5500")

    # --- Error tracking (Sentry) ---
    # If unset, no error tracking is initialized — the app runs exactly as
    # it does today. Set this in production so a broken deployment shows up
    # somewhere other than "nobody noticed until a client complained."
    SENTRY_DSN = os.environ.get("SENTRY_DSN")

    # --- Cloudinary (File Storage) ---
    CLOUDINARY_URL = os.environ.get("CLOUDINARY_URL")


class DevConfig(Config):
    DEBUG = True
    # Local-only fallback so a dev can run the app without provisioning
    # Postgres immediately. NEVER used in production — production always
    # requires a real DATABASE_URL (enforced in app.py).
    SQLALCHEMY_DATABASE_URI = (
        Config.SQLALCHEMY_DATABASE_URI or "sqlite:///dev_local_only.db"
    )
    # Re-derive engine options against the *actual* URI in use here, not
    # Config's (which was computed before this sqlite fallback existed) —
    # otherwise a local run with no DATABASE_URL set inherits a
    # connect_args={"connect_timeout": ...} meant for MySQL/Postgres, and
    # sqlite3's DBAPI throws on an argument it doesn't recognize.
    SQLALCHEMY_ENGINE_OPTIONS = (
        {"poolclass": Config.SQLALCHEMY_ENGINE_OPTIONS["poolclass"]}
        if SQLALCHEMY_DATABASE_URI.startswith("sqlite")
        else Config.SQLALCHEMY_ENGINE_OPTIONS
    )
    JWT_COOKIE_SECURE = False
    CORS_ORIGINS = Config.CORS_ORIGINS or ["http://localhost:5500", "http://127.0.0.1:5500"]


class ProductionConfig(Config):
    DEBUG = False
