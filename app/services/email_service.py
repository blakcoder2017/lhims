"""
Email Service for sending password reset emails
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
import os

# Email configuration (can be moved to settings)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_password_reset_email(email: str, reset_link: str, user_name: Optional[str] = None) -> bool:
    """
    Send password reset email
    
    Returns True if sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        # Log warning: Email not configured
        print(f"WARNING: Email not configured. Would send reset link to {email}: {reset_link}")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_FROM
        msg['To'] = email
        msg['Subject'] = "LHIMS Password Reset Request"
        
        user_greeting = f"Hello {user_name}," if user_name else "Hello,"
        
        body = f"""
{user_greeting}

You requested a password reset for your LHIMS account.

Click the link below to reset your password:
{reset_link}

This link will expire in 24 hours.

If you did not request this password reset, please ignore this email. Your password will remain unchanged.

Best regards,
LHIMS Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

