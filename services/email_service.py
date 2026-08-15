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


def send_product_release_notification(email: str, product_name: str, shop_url: str) -> None:
    """Notify a subscriber that a coming-soon product is now available."""
    _send(
        to=email,
        subject=f"'{product_name}' is now available — Empowered Me Wellness",
        html=f"""
        <div style="font-family: 'Lato', Arial, sans-serif; max-width: 560px; margin: 0 auto; color: #241C13;">
          <p style="font-size: 18px; line-height: 1.6;">Great news!</p>
          <p style="font-size: 16px; line-height: 1.6;">
            <strong>{product_name}</strong> is now available for purchase.
            You asked to be notified when it launched — here it is!
          </p>
          <p style="margin: 28px 0;">
            <a href="{shop_url}"
               style="display: inline-block; padding: 14px 32px; background: #B05535;
                      color: #F2EDE0; text-decoration: none; border-radius: 10px;
                      font-weight: 600; font-size: 16px;">
              Get Your Copy
            </a>
          </p>
          <p style="font-size: 14px; color: #888;">
            — Empowered Me Wellness
          </p>
        </div>
        """,
    )


def send_order_confirmation(order) -> None:
    """
    Sent once an order transitions to 'paid' — called from whichever path
    detected that: the dev-only simulation, the Stripe webhook, or the
    self-healing sync. Mirrors send_booking_confirmation's role for bookings.

    This links to the order-confirmation page rather than baking in a raw
    /files/download/<token> URL directly: download tokens expire after
    DOWNLOAD_LINK_EXPIRY_SECONDS (short-lived, by design — see
    download_service.py), but this email might be opened days later. The
    page itself generates a fresh, valid download link at click time
    instead, the same way it already does right after a live Stripe
    redirect — this just makes that path reachable from a cold open too.
    """
    from urllib.parse import quote

    to = order.contact_email()
    if not to:
        logger.warning(
            "Order %s reached 'paid' with no contact email on file — "
            "skipping confirmation email (nothing to send it to).",
            order.id,
        )
        return

    base = current_app.config["FRONTEND_BASE_URL"].rstrip("/")
    is_guest = order.user_id is None

    items_html = ""
    for item in order.items:
        product = item.product
        if not product:
            continue
        link = (
            f"{base}/order-confirmation.html"
            f"?order_id={order.id}&product_id={product.id}&product_name={quote(product.name)}"
        )
        if is_guest:
            link += f"&email={quote(to)}"
        items_html += f"""
        <p style="margin: 20px 0;">
          <strong>{product.name}</strong><br>
          <a href="{link}"
             style="display:inline-block; margin-top:8px; padding:12px 28px; background:#B05535;
                    color:#F2EDE0; text-decoration:none; border-radius:10px; font-weight:600;">
            Download your copy
          </a>
        </p>
        """

    _send(
        to=to,
        subject="Your Empowered Me Wellness order is ready",
        html=f"""
        <div style="font-family: 'Lato', Arial, sans-serif; max-width: 560px; margin: 0 auto; color: #241C13;">
          <p style="font-size: 18px;">Thank you for your purchase!</p>
          {items_html}
          <p style="font-size: 14px; color: #888;">
            Keep this email — you can come back and use this link any time to re-download your purchase.
          </p>
          <p style="font-size: 14px; color: #888;">— Empowered Me Wellness</p>
        </div>
        """,
    )
