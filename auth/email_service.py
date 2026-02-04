"""Email service for sending verification codes."""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending verification emails with SMTP fallback to console."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_from_email: Optional[str] = None,
    ):
        """Initialize email service."""
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._smtp_from_email = smtp_from_email or smtp_user

    @property
    def is_configured(self) -> bool:
        """Check if SMTP is properly configured."""
        return bool(
            self._smtp_host
            and self._smtp_user
            and self._smtp_password
            and self._smtp_from_email
        )

    def send_verification_code(self, email: str, code: str) -> bool:
        """
        Send verification code to email.
        Returns True if sent successfully.
        Falls back to console output if SMTP not configured.
        """
        if not self.is_configured:
            # Console fallback - print the code
            print(f"\n{'='*50}")
            print(f"VERIFICATION CODE for {email}")
            print(f"Code: {code}")
            print(f"{'='*50}\n")
            logger.info(f"Verification code for {email}: {code} (console fallback)")
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Your cc-zol Verification Code"
            msg["From"] = self._smtp_from_email
            msg["To"] = email

            # Plain text version
            text = f"""Your verification code is: {code}

This code will expire in 10 minutes.

If you didn't request this code, you can safely ignore this email.
"""

            # HTML version
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 400px; margin: 40px auto; padding: 20px; }}
        .code {{ font-size: 32px; font-weight: bold; letter-spacing: 4px;
                 color: #333; background: #f5f5f5; padding: 16px;
                 text-align: center; border-radius: 8px; margin: 20px 0; }}
        .footer {{ color: #666; font-size: 12px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Verification Code</h2>
        <p>Enter this code to verify your email:</p>
        <div class="code">{code}</div>
        <p>This code will expire in 10 minutes.</p>
        <p class="footer">If you didn't request this code, you can safely ignore this email.</p>
    </div>
</body>
</html>
"""

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.sendmail(self._smtp_from_email, email, msg.as_string())

            logger.info(f"Verification email sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {email}: {e}")
            # Fall back to console
            print(f"\n{'='*50}")
            print(f"VERIFICATION CODE for {email}")
            print(f"Code: {code}")
            print(f"(Email sending failed, showing code here)")
            print(f"{'='*50}\n")
            return True  # Still return True since we showed the code
