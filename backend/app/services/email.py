"""
Email service for AI Interview Simulator.

Sends transactional emails via SMTP.
If SMTP is not configured (SMTP_HOST is None), the email content is
logged to the console — safe dev fallback, no external dependency.

NEVER log raw tokens, passwords, or PII in production.
"""
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HTML email template
# ---------------------------------------------------------------------------

def _build_reset_email_html(reset_url: str, expires_minutes: int) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Password Reset — AI Interview</title>
<style>
  body {{
    margin: 0; padding: 0;
    background-color: #070A12;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    color: #F8FAFC;
  }}
  .wrapper {{
    max-width: 560px;
    margin: 40px auto;
    padding: 0 16px;
  }}
  .header {{
    text-align: center;
    margin-bottom: 32px;
  }}
  .logo-icon {{
    display: inline-block;
    width: 48px; height: 48px;
    background: linear-gradient(135deg, #6366f1, #22d3ee);
    border-radius: 12px;
    line-height: 48px;
    font-size: 24px;
    text-align: center;
    margin-bottom: 12px;
  }}
  .brand-name {{
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.5px;
    color: #fff;
    margin: 0;
  }}
  .brand-sub {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #22d3ee;
    margin: 4px 0 0;
  }}
  .card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 40px 36px;
  }}
  h1 {{
    font-size: 20px;
    font-weight: 700;
    color: #fff;
    margin: 0 0 12px;
  }}
  p {{
    font-size: 15px;
    line-height: 1.6;
    color: #94a3b8;
    margin: 0 0 24px;
  }}
  .btn {{
    display: inline-block;
    padding: 14px 32px;
    background: linear-gradient(135deg, #6366f1, #4f46e5);
    color: #fff !important;
    text-decoration: none;
    font-size: 15px;
    font-weight: 700;
    border-radius: 12px;
    letter-spacing: 0.3px;
  }}
  .btn-wrap {{
    text-align: center;
    margin-bottom: 28px;
  }}
  .divider {{
    border: none;
    border-top: 1px solid rgba(255,255,255,0.07);
    margin: 28px 0;
  }}
  .note {{
    font-size: 13px;
    color: #64748b;
    line-height: 1.6;
    margin: 0;
  }}
  .note a {{
    color: #818cf8;
    word-break: break-all;
  }}
  .expiry-badge {{
    display: inline-block;
    background: rgba(251,191,36,0.12);
    color: #fbbf24;
    font-size: 12px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 6px;
    margin-bottom: 20px;
  }}
  .footer {{
    text-align: center;
    margin-top: 28px;
    font-size: 12px;
    color: #334155;
  }}
</style>
</head>
<body>
<div class="wrapper">
  <div class="header">
    <div class="logo-icon">✦</div>
    <p class="brand-name">AI Interview</p>
    <p class="brand-sub">Simulator SaaS</p>
  </div>

  <div class="card">
    <h1>Password Reset Request</h1>
    <p>We received a request to reset the password for your AI Interview account.
       Click the button below to create a new password.</p>

    <div class="expiry-badge">⏱ Link expires in {expires_minutes} minutes</div>

    <div class="btn-wrap">
      <a class="btn" href="{reset_url}">Reset Password</a>
    </div>

    <hr class="divider" />

    <p class="note">
      If the button doesn't work, copy and paste this link into your browser:<br/>
      <a href="{reset_url}">{reset_url}</a>
    </p>

    <p class="note" style="margin-top:16px;">
      If you did not request a password reset, you can safely ignore this email.
      Your password will remain unchanged.
    </p>
  </div>

  <div class="footer">
    © AI Interview Simulator · This is an automated message, please do not reply.
  </div>
</div>
</body>
</html>"""


def _build_reset_email_text(reset_url: str, expires_minutes: int) -> str:
    return (
        f"AI Interview — Password Reset Request\n\n"
        f"We received a request to reset your password.\n\n"
        f"Reset your password here (link expires in {expires_minutes} minutes):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email.\n"
        f"Your password will remain unchanged.\n\n"
        f"— AI Interview Simulator"
    )


# ---------------------------------------------------------------------------
# Public send function
# ---------------------------------------------------------------------------

def send_password_reset_email(
    to_email: str,
    reset_url: str,
    expires_minutes: int | None = None,
) -> None:
    """
    Send a password-reset email to `to_email`.

    In development (SMTP_HOST not configured) the reset URL is printed to
    the console so the developer can test the flow without a real mail server.
    """
    if expires_minutes is None:
        expires_minutes = settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES

    subject = "Reset your AI Interview password"
    html_body = _build_reset_email_html(reset_url, expires_minutes)
    text_body = _build_reset_email_text(reset_url, expires_minutes)

    if not settings.SMTP_HOST:
        # Dev fallback — log so developer can click the link
        logger.warning(
            "[DEV] SMTP not configured. Password reset URL for %s:\n%s",
            to_email,
            reset_url,
        )
        print(
            f"\n{'='*60}\n"
            f"[DEV] PASSWORD RESET LINK (no SMTP configured)\n"
            f"To: {to_email}\n"
            f"URL: {reset_url}\n"
            f"{'='*60}\n"
        )
        return

    # Build MIME message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to_email

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        if settings.SMTP_USE_TLS:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls(context=context)
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info("Password reset email sent to %s", to_email)

    except Exception as exc:
        # Log error but do NOT re-raise — the API layer must still return
        # the same generic success message regardless to prevent enumeration.
        logger.error("Failed to send password reset email to %s: %s", to_email, exc)
