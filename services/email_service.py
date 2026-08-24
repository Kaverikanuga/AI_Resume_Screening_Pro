"""
Email Service
Sends transactional emails through the already-configured Flask-Mail extension.

Behavior:
- When MAIL_USERNAME/MAIL_PASSWORD are configured, emails are delivered via SMTP.
- When mail is NOT configured (local development), senders return False and the
  calling route falls back to its existing development behavior (e.g., flashing
  the reset link) so nothing breaks in local workflows.
"""
import logging

from flask import current_app, render_template
from extensions import mail

try:
    from flask_mail import Message
    HAS_FLASK_MAIL = True
except ImportError:
    HAS_FLASK_MAIL = False

logger = logging.getLogger(__name__)

RESET_BODY_TEMPLATE = (
    "Hi {name},\n\n"
    "We received a request to reset your password.\n\n"
    "Open this link within the next hour to choose a new password:\n"
    "{reset_url}\n\n"
    "If you did not request this, you can safely ignore this email.\n\n"
    "- AI Resume Screening Pro Team"
)

CONTACT_ACK_TEMPLATE = (
    "Hi {name},\n\n"
    "Thanks for reaching out! Our team will get back to you shortly.\n\n"
    "- AI Resume Screening Pro Team"
)


def _mail_configured() -> bool:
    if not HAS_FLASK_MAIL:
        return False
    return bool(current_app.config.get('MAIL_USERNAME')) and bool(current_app.config.get('MAIL_PASSWORD'))


def send_password_reset_email(user, reset_url: str) -> bool:
    """Send the password-reset email. Returns True when actually sent."""
    if not _mail_configured():
        logger.info("Mail not configured - skipping password-reset email delivery.")
        return False

    try:
        msg = Message(
            subject='Reset Your Password - AI Resume Screening Pro',
            recipients=[user.email],
            body=RESET_BODY_TEMPLATE.format(name=user.name, reset_url=reset_url),
        )
        try:
            msg.html = render_template('emails/reset_password.html', user=user, reset_url=reset_url)
        except Exception:
            pass  # plain-text fallback is sufficient
        mail.send(msg)
        logger.info("Password reset email sent to %s", user.email)
        return True
    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}", exc_info=True)
        return False


def send_contact_acknowledgement(name: str, email_addr: str) -> bool:
    """Optional acknowledgement for contact-form submissions (best effort)."""
    if not _mail_configured():
        return False
    try:
        msg = Message(
            subject='We received your message - AI Resume Screening Pro',
            recipients=[email_addr],
            body=CONTACT_ACK_TEMPLATE.format(name=name),
        )
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Contact acknowledgement failed: {e}", exc_info=True)
        return False