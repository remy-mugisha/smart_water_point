from flask import current_app, render_template
from flask_mail import Message


def _masked(value):
    if not value:
        return "<not set>"
    return f"{value[:4]}...{value[-4:]} (len={len(value)})"


def log_smtp_config():
    """Log the resolved SMTP settings (password masked) before a send."""
    cfg = current_app.config
    current_app.logger.info(
        "SMTP connect: server=%(server)s port=%(port)s tls=%(tls)s user=%(username)s "
        "pass=%(password)s sender=%(sender)s",
        {
            "server": cfg.get("MAIL_SERVER"),
            "port": cfg.get("MAIL_PORT"),
            "tls": cfg.get("MAIL_USE_TLS"),
            "username": cfg.get("MAIL_USERNAME") or "<not set>",
            "password": _masked(cfg.get("MAIL_PASSWORD")),
            "sender": cfg.get("MAIL_DEFAULT_SENDER"),
        },
    )


def smtp_error_hint(exc):
    text = str(exc)
    if "535" in text or "Authentication" in text:
        return (
            "SMTP login rejected (535). SMTP_USER must be a Gmail address and SMTP_PASS "
            "the 16-character App Password created for it (Google Account > Security > "
            "2-Step Verification > App passwords). Note: a revoked App Password invalidates "
            "the old one. Restart the server after editing .env - the reloader does not "
            "watch .env."
        )
    if any(token in text for token in ("550", "553", "Sender", "5.7.1")):
        return (
            "Sender address rejected. MAIL_FROM must be your own Gmail address (the same "
            "account used for SMTP_USER) - Gmail does not allow sending from a different "
            "address."
        )
    return "Check network access and that SMTP_HOST/SMTP_PORT are reachable."


def send_email(to_email, to_name, subject, html_content):
    """Send an HTML email via SMTP (Gmail) using Flask-Mail.

    Raises on any failure (missing config, network error, or SMTP error)
    so existing try/except / audit-log / flash-message handling keeps working.
    """
    if not current_app.config.get("MAIL_USERNAME") or not current_app.config.get("MAIL_PASSWORD"):
        raise RuntimeError(
            "SMTP_USER / SMTP_PASS are not configured - add them to the environment "
            "variables (Gmail address + App Password)."
        )

    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME")
    if not sender:
        raise RuntimeError("MAIL_FROM is not configured.")

    from app import mail

    msg = Message(
        subject=subject,
        recipients=[to_email],
        html=html_content,
        sender=sender,
    )
    mail.send(msg)


def send_welcome_email(recipient_email, recipient_name, temp_password, login_url):
    try:
        html_body = render_template(
            "emails/welcome_technician.html",
            name=recipient_name,
            email=recipient_email,
            temp_password=temp_password,
            login_url=login_url,
            app_name=current_app.config.get("APP_NAME", "AI-BASED WATER POINT FAILURE PREDICTION SYSTEM"),
        )
        send_email(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=f"Welcome to {current_app.config.get('APP_NAME', 'AI-BASED WATER POINT FAILURE PREDICTION SYSTEM')}",
            html_content=html_body,
        )
        return True, None
    except Exception as exc:
        current_app.logger.error(
            "Failed to send welcome email to %s: %s - %s",
            recipient_email,
            exc,
            smtp_error_hint(exc),
            exc_info=True,
        )
        return False, f"{exc} - {smtp_error_hint(exc)}"
