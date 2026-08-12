import os

import requests
from flask import current_app, render_template

BREVO_SEND_URL = "https://api.brevo.com/v3/smtp/email"


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
    if "Brevo" in text or "api key" in text.lower():
        return (
            "Brevo HTTP API error. Verify BREVO_API_KEY is set in the Render "
            "environment (starts with 'xkeysib-') and that the sender address "
            "(MAIL_FROM / MAIL_DEFAULT_SENDER) is verified in the Brevo dashboard "
            "(Account > Senders)."
        )
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


def send_email_via_brevo(to_email, to_name, subject, html_content):
    """Send an HTML email via Brevo's REST API over HTTPS (not SMTP).

    Raises on any failure (missing config, network error, or non-2xx response)
    so existing try/except / audit-log / flash-message handling keeps working.
    """
    api_key = current_app.config.get("BREVO_API_KEY") or os.environ.get("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured - add it to the Render environment variables.")

    sender_email = current_app.config.get("MAIL_DEFAULT_SENDER")
    if not sender_email:
        raise RuntimeError("MAIL_DEFAULT_SENDER / MAIL_FROM is not configured.")

    response = requests.post(
        BREVO_SEND_URL,
        headers={
            "api-key": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "sender": {
                "email": sender_email,
                "name": current_app.config.get("APP_NAME", "Smart Water Point Monitoring System"),
            },
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": html_content,
        },
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise RuntimeError(
            f"Brevo API returned HTTP {response.status_code}: {response.text}"
        ) from exc


def send_welcome_email(recipient_email, recipient_name, temp_password, login_url):
    try:
        html_body = render_template(
            "emails/welcome_technician.html",
            name=recipient_name,
            email=recipient_email,
            temp_password=temp_password,
            login_url=login_url,
            app_name=current_app.config.get("APP_NAME", "Smart Water Point Monitoring System"),
        )
        send_email_via_brevo(
            to_email=recipient_email,
            to_name=recipient_name,
            subject=f"Welcome to {current_app.config.get('APP_NAME', 'Smart Water Monitoring')}",
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
