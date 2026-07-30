import logging

from flask import jsonify

logger = logging.getLogger("emw")


def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": {"message": "Not found.", "code": "not_found"}}), 404

    @app.errorhandler(405)
    def method_not_allowed(e):
        return (
            jsonify({"error": {"message": "Method not allowed.", "code": "method_not_allowed"}}),
            405,
        )

    @app.errorhandler(429)
    def rate_limited(e):
        return (
            jsonify(
                {
                    "error": {
                        "message": "Too many requests. Please try again shortly.",
                        "code": "rate_limited",
                    }
                }
            ),
            429,
        )

    @app.errorhandler(Exception)
    def unhandled_exception(e):
        # Full detail goes to the server log only. The client never sees a
        # stack trace, file path, or database error string.
        logger.exception("Unhandled exception")
        return (
            jsonify(
                {
                    "error": {
                        "message": "Something went wrong on our end. Please try again.",
                        "code": "internal_error",
                    }
                }
            ),
            500,
        )
