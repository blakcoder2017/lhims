"""
Password Reset Service
Handles token generation, validation, and management for password resets
"""
import secrets
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.password_reset_models import PasswordResetToken
from app.models.user_models import User


def generate_reset_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)


def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    return ''.join([str(secrets.randbelow(10)) for _ in range(6)])


def create_email_reset_token(db: Session, user: User, email: str) -> PasswordResetToken:
    """Create email-based password reset token"""
    # Invalidate existing tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})
    
    token = generate_reset_token()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        token_type='email',
        email=email,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def create_sms_reset_token(db: Session, user: User, phone_number: str) -> PasswordResetToken:
    """Create SMS-based password reset token (OTP)"""
    # Invalidate existing tokens
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False
    ).update({"used": True})
    
    otp = generate_otp()
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=secrets.token_urlsafe(32),  # Internal token
        token_type='sms',
        phone_number=phone_number,
        otp_code=otp,
        expires_at=datetime.utcnow() + timedelta(minutes=15)  # OTP expires in 15 min
    )
    db.add(reset_token)
    db.commit()
    db.refresh(reset_token)
    return reset_token


def verify_reset_token(db: Session, token: str) -> PasswordResetToken:
    """Verify and return valid reset token"""
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    return reset_token


def verify_otp(db: Session, user_id: int, otp: str) -> PasswordResetToken:
    """Verify OTP and return valid reset token"""
    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.otp_code == otp,
        PasswordResetToken.used == False,
        PasswordResetToken.expires_at > datetime.utcnow()
    ).first()
    return reset_token


def mark_token_used(db: Session, token_id: int):
    """Mark reset token as used"""
    db.query(PasswordResetToken).filter(
        PasswordResetToken.id == token_id
    ).update({"used": True})
    db.commit()

