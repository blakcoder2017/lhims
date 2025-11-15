"""
Password Reset Token Models
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    token_type = Column(String(20), nullable=False)  # 'email' or 'sms'
    phone_number = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    otp_code = Column(String(6), nullable=True)  # For SMS OTP
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    user = relationship("User", backref="password_reset_tokens")
    
    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, token_type={self.token_type}, used={self.used})>"

