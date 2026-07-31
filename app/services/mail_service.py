from flask import current_app, render_template
from flask_mail import Message

from app import mail


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
            "SMTP login rejected (535). SMTP_USER must be the Brevo account login email "
            "and SMTP_PASS the current SMTP key from the Brevo dashboard (SMTP & API > SMTP). "
            "Note: a regenerated SMTP key invalidates the old one. Restart the server after "
            "editing .env - the reloader does not watch .env."
        )
    if any(token in text for token in ("550", "553", "Sender", "5.7.1")):
        return (
            "Sender address rejected. The MAIL_FROM domain must be verified in the Brevo "
            "dashboard (Account > Senders), or use b3e2a0001@smtp-brevo.com to test."
        )
    return "Check network access and that SMTP_HOST/SMTP_PORT are reachable."


def send_welcome_email(recipient_email, recipient_name, temp_password, login_url):
    try:
        log_smtp_config()
        html_body = render_template(
            "emails/welcome_technician.html",
            name=recipient_name,
            email=recipient_email,
            temp_password=temp_password,
            login_url=login_url,
            app_name=current_app.config.get("APP_NAME", "Smart Water Point Monitoring System"),
        )
        msg = Message(
            subject=f"Welcome to {current_app.config.get('APP_NAME', 'Smart Water Monitoring')}",
            recipients=[recipient_email],
            html=html_body,
        )
        mail.send(msg)
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
