import logging

from flask import current_app

logger = logging.getLogger("emw")


def _resend_configured() -> bool:
    return bool(current_app.config.get("RESEND_API_KEY"))


def _send(to: str, subject: str, html: str) -> None:
    """
    The single choke point every email in this codebase goes through.

    If RESEND_API_KEY is configured, sends for real via Resend. If not
    (local dev), logs the email content instead — the same dev-only
    simulation pattern used for Stripe checkout and password reset links
    elsewhere in this codebase, and hard-disabled in production by the
    same kind of check.
    """
    if current_app.config.get("FLASK_ENV") == "production" and not _resend_configured():
        logger.error(
            "Email not configured in production — refusing to silently drop a "
            "real email to %s (subject: %s). Set RESEND_API_KEY.",
            to,
            subject,
        )
        return

    if not _resend_configured():
        logger.warning(
            "DEV-ONLY EMAIL SIMULATION (would be sent via Resend in production):\n"
            "  To: %s\n  Subject: %s\n  Body:\n%s",
            to,
            subject,
            html,
        )
        return

    import resend

    resend.api_key = current_app.config["RESEND_API_KEY"]
    from_address = current_app.config.get("EMAIL_FROM_ADDRESS", "no-reply@empoweredmewellness.com")

    try:
        resend.Emails.send(
            {"from": from_address, "to": [to], "subject": subject, "html": html}
        )
    except Exception:
        logger.exception("Failed to send email to %s (subject: %s)", to, subject)


def send_booking_confirmation(booking) -> None:
    session = booking.session
    dt = session.start_time
    formatted = dt.strftime("%A, %B {d} at {t}").format(
        d=str(dt.day),
        t=dt.strftime("%I:%M %p").lstrip("0")
    )
    _send(
        to=booking.contact_email(),
        subject=f"Booking confirmed: {session.title}",
        html=f"""
        <p>Hi {booking.contact_name()},</p>
        <p>You're confirmed for <strong>{session.title}</strong>
        on {formatted} at {session.location}.</p>
        <p>See you there!</p>
        <p>— Empowered Me Wellness</p>
        """,
    )


def send_booking_reminder(booking) -> None:
    session = booking.session
    dt = session.start_time
    formatted = dt.strftime("%A, %B {d} at {t}").format(
        d=str(dt.day),
        t=dt.strftime("%I:%M %p").lstrip("0")
    )
    _send(
        to=booking.contact_email(),
        subject=f"Reminder: {session.title} is coming up",
        html=f"""
        <p>Hi {booking.contact_name()},</p>
        <p>Just a reminder — <strong>{session.title}</strong> is coming up
        on {formatted} at {session.location}.</p>
        <p>— Empowered Me Wellness</p>
        """,
    )


def send_cancellation_notice(booking) -> None:
    session = booking.session
    dt = session.start_time
    formatted = dt.strftime("%A, %B {d} at {t}").format(
        d=str(dt.day),
        t=dt.strftime("%I:%M %p").lstrip("0")
    )
    _send(
        to=booking.contact_email(),
        subject=f"Cancelled: {session.title}",
        html=f"""
        <p>Hi {booking.contact_name()},</p>
        <p>Your booking for <strong>{session.title}</strong>
        on {formatted} has been cancelled.</p>
        <p>If you have questions, just reply to this email.</p>
        <p>— Empowered Me Wellness</p>
        """,
    )


def send_password_reset(email: str, reset_link: str) -> None:
    _send(
        to=email,
        subject="Reset your Empowered Me Wellness password",
        html=f"""
        <p>Someone requested a password reset for this account.</p>
        <p><a href="{reset_link}">Click here to set a new password</a>. This link expires in 30 minutes.</p>
        <p>If you didn't request this, you can safely ignore this email.</p>
        """,
    )
