"""
Notification utilities: WhatsApp via Twilio, Email via SMTP.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_whatsapp(message: str) -> dict:
    """
    Send a WhatsApp message via Twilio.
    Returns dict with status and message_sid.
    """
    try:
        from twilio.rest import Client

        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            logger.warning("Twilio credentials not configured. Skipping WhatsApp.")
            return {"status": "skipped", "reason": "Twilio not configured"}

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            from_=settings.WHATSAPP_FROM,
            to=settings.WHATSAPP_TO,
            body=message,
        )
        logger.info(f"WhatsApp sent: SID={msg.sid}")
        return {"status": "sent", "sid": msg.sid}
    except ImportError:
        logger.error("twilio package not installed.")
        return {"status": "error", "reason": "twilio not installed"}
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return {"status": "error", "reason": str(e)}


def send_email(subject: str, body_html: str, to_email: str | None = None) -> dict:
    """
    Send an HTML email via SMTP (Gmail by default).
    """
    recipient = to_email or settings.EMAIL_TO or settings.EMAIL_USER
    if not settings.EMAIL_USER or not settings.EMAIL_PASS:
        logger.warning("Email credentials not configured. Skipping email.")
        return {"status": "skipped", "reason": "Email not configured"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_USER
        msg["To"] = recipient

        part = MIMEText(body_html, "html")
        msg.attach(part)

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASS)
            server.sendmail(settings.EMAIL_USER, recipient, msg.as_string())

        logger.info(f"Email sent to {recipient}: {subject}")
        return {"status": "sent", "recipient": recipient}
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return {"status": "error", "reason": str(e)}


def build_job_notification_message(matches: list[dict]) -> tuple[str, str]:
    """
    Build WhatsApp text and HTML email body from top matches.

    Returns:
        (whatsapp_text, email_html)
    """
    top = matches[:5]  # Notify top 5 matches

    # WhatsApp plain text
    wa_lines = ["🎯 *New Job Matches Found!*\n"]
    for i, m in enumerate(top, 1):
        wa_lines.append(
            f"{i}. *{m.get('title')}* @ {m.get('company')}\n"
            f"   📍 {m.get('location', 'N/A')} | ✅ Match: {m.get('match_score', 0):.1f}%\n"
            f"   {m.get('url', '')}\n"
        )
    wa_text = "\n".join(wa_lines)

    # HTML email
    rows = ""
    for m in top:
        score = m.get("match_score", 0)
        color = "#22c55e" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"
        rows += f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;">
            <strong>{m.get('title')}</strong><br>
            <span style="color:#6b7280;">{m.get('company')} · {m.get('location','N/A')}</span>
          </td>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;text-align:center;">
            <span style="background:{color};color:#fff;padding:4px 10px;border-radius:12px;font-weight:bold;">
              {score:.1f}%
            </span>
          </td>
          <td style="padding:12px;border-bottom:1px solid #e5e7eb;">
            <a href="{m.get('url','#')}" style="color:#6366f1;text-decoration:none;">View Job →</a>
          </td>
        </tr>
        """

    email_html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f9fafb;padding:20px;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
        <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:24px;text-align:center;">
          <h1 style="color:#fff;margin:0;">🎯 New Job Matches</h1>
          <p style="color:#c7d2fe;margin:8px 0 0;">Your AI-powered job tracker found new opportunities!</p>
        </div>
        <div style="padding:24px;">
          <table style="width:100%;border-collapse:collapse;">
            <thead>
              <tr style="background:#f3f4f6;">
                <th style="padding:12px;text-align:left;">Position</th>
                <th style="padding:12px;text-align:center;">Match</th>
                <th style="padding:12px;text-align:left;">Link</th>
              </tr>
            </thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
        <div style="padding:16px;background:#f9fafb;text-align:center;color:#9ca3af;font-size:12px;">
          Sent by Job Tracker · Unsubscribe by updating your notification settings
        </div>
      </div>
    </body></html>
    """

    return wa_text, email_html
