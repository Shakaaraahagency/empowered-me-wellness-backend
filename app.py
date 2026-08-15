import os

from flask import Flask

from config import DevConfig, ProductionConfig
from extensions import db, migrate, jwt, cors, limiter
from middleware.error_handlers import register_error_handlers


def create_app():
    env = os.environ.get("FLASK_ENV", "development")

    # Sentry must be initialized before the Flask app object is created to
    # catch startup-time errors too. Reads the env var directly rather than
    # from app.config, which doesn't exist yet at this point.
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[FlaskIntegration()],
            environment=env,
            # Sends error events, not full request tracing — keep overhead low.
            traces_sample_rate=0.0,
        )

    app = Flask(__name__)

    app.config["FLASK_ENV"] = env  # so checks like payment_service's prod guard can see it

    if env == "production":
        app.config.from_object(ProductionConfig)
        if not app.config["SQLALCHEMY_DATABASE_URI"]:
            raise RuntimeError(
                "DATABASE_URL is not set. Refusing to start in production "
                "without a real Postgres connection."
            )
        if not app.config["SECRET_KEY"] or not app.config["JWT_SECRET_KEY"]:
            raise RuntimeError(
                "SECRET_KEY / JWT_SECRET_KEY must be set via environment "
                "variables in production."
            )
    else:
        app.config.from_object(DevConfig)
        # Local-only fallback secrets so `flask run` works out of the box.
        # These are never used in production — see the check above.
        # (Using explicit checks, not setdefault: from_object already sets
        # these keys to None via os.environ.get, so setdefault would no-op.)
        if not app.config.get("SECRET_KEY"):
            app.config["SECRET_KEY"] = "dev-only-not-for-production"
        if not app.config.get("JWT_SECRET_KEY"):
            app.config["JWT_SECRET_KEY"] = "dev-only-not-for-production"

    # --- extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    if app.config.get("CLOUDINARY_URL"):
        import cloudinary
        # The cloudinary package automatically reads CLOUDINARY_URL from the
        # environment, but we can explicitly configure it to enforce secure URLs.
        cloudinary.config(secure=True)

    # --- models must be imported before creating tables / running migrations ---
    from models.user import User, TokenBlocklist  # noqa: F401
    from models.contact_message import ContactMessage  # noqa: F401
    from models.class_ import Class, Session  # noqa: F401
    from models.product import Product  # noqa: F401
    from models.product_review import ProductReview  # noqa: F401
    from models.booking import Booking  # noqa: F401
    from models.order import Order, OrderItem, Payment  # noqa: F401
    from models.password_reset_token import PasswordResetToken  # noqa: F401
    from models.testimonial import Testimonial  # noqa: F401
    from models.blog_post import BlogPost  # noqa: F401
    from models.newsletter import NewsletterSubscriber  # noqa: F401
    from models.product_notification import ProductNotification  # noqa: F401

    # --- JWT blocklist check: this is what makes logout a real revocation ---
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = TokenBlocklist.query.filter_by(jti=jti).first()
        return token is not None and token.revoked

    # --- blueprints (controllers) ---
    from routes.auth import auth_bp
    from routes.contact import contact_bp
    from routes.sessions import sessions_bp
    from routes.bookings import bookings_bp
    from routes.admin.sessions_admin import sessions_admin_bp
    from routes.admin.products_admin import products_admin_bp
    from routes.admin.bookings_admin import bookings_admin_bp
    from routes.admin.orders_admin import orders_admin_bp
    from routes.admin.testimonials_admin import testimonials_admin_bp
    from routes.admin.contact_admin import contact_admin_bp
    from routes.admin.stats_admin import stats_admin_bp
    from routes.admin.blog_admin import blog_admin_bp
    from routes.admin.subscribers_admin import subscribers_admin_bp
    from routes.products import products_bp
    from routes.orders import orders_bp
    from routes.testimonials import testimonials_bp
    from routes.blog import blog_bp
    from routes.newsletter import newsletter_bp
    from routes.admin.reviews_admin import reviews_admin_bp

    app.register_blueprint(reviews_admin_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(sessions_admin_bp)
    app.register_blueprint(products_admin_bp)
    app.register_blueprint(bookings_admin_bp)
    app.register_blueprint(orders_admin_bp)
    app.register_blueprint(testimonials_admin_bp)
    app.register_blueprint(contact_admin_bp)
    app.register_blueprint(stats_admin_bp)
    app.register_blueprint(blog_admin_bp)
    app.register_blueprint(subscribers_admin_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(testimonials_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(newsletter_bp)

    register_error_handlers(app)

    # --- Security headers on every response ---
    # Render terminates TLS, so HSTS/etc. are safe to set unconditionally
    # for the API's own responses. CSP is intentionally left off here: this
    # is a JSON API, not an HTML-serving app, so there's no inline
    # script/style surface for CSP to restrict — the frontend (a separate
    # static Hostinger deploy) is where CSP would apply, not this backend.
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        if env == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.route("/api/v1/health", methods=["GET"])
    def health():
        return {"status": "ok"}, 200

    @app.route("/public/<path:filename>", methods=["GET"])
    def serve_public_file(filename):
        from flask import send_from_directory
        public_dir = os.path.join(app.root_path, "public")
        return send_from_directory(public_dir, filename)

    # --- CLI: bootstrap the first admin account ---
    # Deliberately NOT an API endpoint — "make me an admin" must never be a
    # request anyone can send. Run with: flask create-admin someone@example.com
    import click

    @app.cli.command("create-admin")
    def create_admin():
        import click

        email = click.prompt("Admin email").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user:
            click.echo(f"No account found for {email}. Register the account first, then run this again.")
            return
        user.role = "admin"
        db.session.commit()
        click.echo(f"{email} is now an admin.")

    @app.cli.command("send-reminders")
    def send_reminders_command():
        import click
        from services.reminder_service import send_due_reminders

        sent = send_due_reminders()
        click.echo(f"Sent {len(sent)} reminder(s).")

    @app.cli.command("cancel-stale-orders")
    @click.option(
        "--hours",
        default=24,
        type=int,
        help="Cancel pending orders older than this many hours (default: 24).",
    )
    def cancel_stale_orders_command(hours):
        import click
        from services.payment_service import cancel_stale_pending_orders

        cancelled = cancel_stale_pending_orders(older_than_hours=hours)
        click.echo(f"Cancelled {len(cancelled)} stale pending order(s).")

    return app


def ensure_database(app):
    """Apply Alembic migrations on startup when running `python app.py` directly.

    Safe to call every time — if the DB file is missing or tables are
    out of date, they are created/updated; if already up to date, this
    is a no-op. Not called under gunicorn/flask run so production deploys
    still use an explicit `flask db upgrade` in the release step.
    """
    from flask_migrate import upgrade
    from sqlalchemy import inspect

    with app.app_context():
        had_tables = bool(inspect(db.engine).get_table_names())
        upgrade(directory="migrations")
        if not had_tables:
            print("Database created and migrations applied.")


app = create_app()

if __name__ == "__main__":
    ensure_database(app)
    app.run(debug=app.config.get("DEBUG", False), port=5000)
