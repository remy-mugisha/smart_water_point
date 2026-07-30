from flask import current_app, render_template
from flask_mail import Message

from app import mail


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
        msg = Message(
            subject=f"Welcome to {current_app.config.get('APP_NAME', 'Smart Water Monitoring')}",
            recipients=[recipient_email],
            html=html_body,
        )
        mail.send(msg)
        return True, None
    except Exception as exc:
        current_app.logger.error("Failed to send welcome email to %s: %s", recipient_email, exc, exc_info=True)
        return False, str(exc)
