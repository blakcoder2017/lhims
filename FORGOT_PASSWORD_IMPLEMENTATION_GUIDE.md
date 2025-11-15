# 🔑 Forgot Password Implementation Guide

## Overview

This guide provides step-by-step instructions for implementing forgot password functionality in LHIMS. The implementation supports both email and SMS-based password reset, suitable for Ghana hospital context.

---

## 📋 Implementation Options

### Option 1: Email-Based Reset (Recommended for Admin/Staff)

**Pros:**
- Free to implement
- Secure token-based
- Works well for staff with email access

**Cons:**
- Requires email server configuration
- May not be accessible to all users

### Option 2: SMS-Based Reset (Recommended for Ghana Context)

**Pros:**
- High accessibility (most users have phones)
- Fast delivery
- Familiar to users

**Cons:**
- Costs per SMS
- Requires SMS gateway integration

### Option 3: Hybrid Approach (Best Practice)

**Implementation:**
- Primary: SMS OTP for password reset
- Fallback: Email token for password reset
- Admin: Can reset passwords directly

---

## 🛠️ Implementation Steps

### Step 1: Database Schema

Add password reset token table:

```python
# migrations/versions/xxxxx_add_password_reset_tokens.py

def upgrade():
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('token_type', sa.String(20), nullable=False),  # 'email' or 'sms'
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('otp_code', sa.String(6), nullable=True),  # For SMS
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('used', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_reset_token', 'password_reset_tokens', ['token'])
    op.create_index('idx_reset_user', 'password_reset_tokens', ['user_id'])
```

### Step 2: Create Models

```python
# app/models/password_reset_models.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import datetime

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
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", backref="password_reset_tokens")
```

### Step 3: Create Services

```python
# app/services/password_reset_service.py

import secrets
import hashlib
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
```

### Step 4: Email Service (Optional)

```python
# app/services/email_service.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_password_reset_email(email: str, reset_link: str):
    """Send password reset email"""
    # Configure SMTP settings in .env
    # SMTP_HOST=smtp.gmail.com
    # SMTP_PORT=587
    # SMTP_USER=your-email@gmail.com
    # SMTP_PASSWORD=your-app-password
    
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = email
    msg['Subject'] = "LHIMS Password Reset Request"
    
    body = f"""
    You requested a password reset for your LHIMS account.
    
    Click the link below to reset your password:
    {reset_link}
    
    This link will expire in 24 hours.
    
    If you did not request this, please ignore this email.
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Send email (implement with your SMTP server)
    # server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
    # server.starttls()
    # server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    # server.send_message(msg)
    # server.quit()
```

### Step 5: SMS Service (Ghana Context)

```python
# app/services/sms_service.py

# Option 1: Using AfricasTalking API (Recommended for Ghana)
# https://africastalking.com/

import requests
from app.core.config import settings

def send_sms_otp(phone_number: str, otp: str):
    """Send SMS OTP using AfricasTalking"""
    # Configure in .env
    # AFRICASTALKING_API_KEY=your-api-key
    # AFRICASTALKING_USERNAME=your-username
    
    url = "https://api.africastalking.com/version1/messaging"
    headers = {
        "ApiKey": settings.AFRICASTALKING_API_KEY,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "username": settings.AFRICASTALKING_USERNAME,
        "to": phone_number,
        "message": f"Your LHIMS password reset OTP is: {otp}. Valid for 15 minutes."
    }
    
    response = requests.post(url, headers=headers, data=data)
    return response.json()

# Option 2: Using Twilio (Alternative)
# Option 3: Using local SMS gateway
```

### Step 6: Create API Routes

```python
# app/routers/password_reset_api.py

from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.user_models import User
from app.services.password_reset_service import (
    create_email_reset_token,
    create_sms_reset_token,
    verify_reset_token,
    verify_otp,
    mark_token_used
)
from app.services.email_service import send_password_reset_email
from app.services.sms_service import send_sms_otp

router = APIRouter(tags=["Password Reset"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/forgot-password", name="forgot_password_page")
def forgot_password_page(request: Request):
    """Forgot password page"""
    return templates.TemplateResponse("auth/forgot_password.html", {"request": request})

@router.post("/forgot-password", name="request_password_reset", status_code=302)
def request_password_reset(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    reset_method: str = Form("sms")  # 'sms' or 'email'
):
    """Request password reset"""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Don't reveal if user exists (security)
        return RedirectResponse(
            url=request.url_for("forgot_password_page") + "?status=sent",
            status_code=302
        )
    
    if reset_method == "email":
        if not user.email:
            return RedirectResponse(
                url=request.url_for("forgot_password_page") + "?error=no_email",
                status_code=302
            )
        reset_token = create_email_reset_token(db, user, user.email)
        reset_link = f"{request.base_url}reset-password?token={reset_token.token}"
        send_password_reset_email(user.email, reset_link)
    
    elif reset_method == "sms":
        # Get phone number from user or request
        phone = request.form.get("phone_number")
        if not phone:
            return RedirectResponse(
                url=request.url_for("forgot_password_page") + "?error=no_phone",
                status_code=302
            )
        reset_token = create_sms_reset_token(db, user, phone)
        send_sms_otp(phone, reset_token.otp_code)
    
    return RedirectResponse(
        url=request.url_for("forgot_password_page") + "?status=sent",
        status_code=302
    )

@router.get("/reset-password", name="reset_password_page")
def reset_password_page(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Query(None),
    user_id: int = Query(None),
    otp: str = Query(None)
):
    """Password reset page"""
    if token:
        reset_token = verify_reset_token(db, token)
        if not reset_token:
            return templates.TemplateResponse(
                "auth/reset_password.html",
                {"request": request, "error": "Invalid or expired token"}
            )
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "token": token, "reset_token": reset_token}
        )
    
    elif user_id and otp:
        reset_token = verify_otp(db, user_id, otp)
        if not reset_token:
            return templates.TemplateResponse(
                "auth/reset_password.html",
                {"request": request, "error": "Invalid or expired OTP"}
            )
        return templates.TemplateResponse(
            "auth/reset_password.html",
            {"request": request, "user_id": user_id, "otp": otp, "reset_token": reset_token}
        )
    
    return templates.TemplateResponse(
        "auth/reset_password.html",
        {"request": request, "error": "Missing reset token or OTP"}
    )

@router.post("/reset-password", name="reset_password", status_code=302)
def reset_password(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(None),
    user_id: int = Form(None),
    otp: str = Form(None),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """Reset password"""
    if new_password != confirm_password:
        return RedirectResponse(
            url=request.url_for("reset_password_page") + f"?token={token}&error=mismatch",
            status_code=302
        )
    
    if len(new_password) < 6:
        return RedirectResponse(
            url=request.url_for("reset_password_page") + f"?token={token}&error=short",
            status_code=302
        )
    
    if token:
        reset_token = verify_reset_token(db, token)
    elif user_id and otp:
        reset_token = verify_otp(db, user_id, otp)
    else:
        return RedirectResponse(
            url=request.url_for("forgot_password_page") + "?error=invalid",
            status_code=302
        )
    
    if not reset_token:
        return RedirectResponse(
            url=request.url_for("forgot_password_page") + "?error=expired",
            status_code=302
        )
    
    # Update password
    user = db.query(User).filter(User.id == reset_token.user_id).first()
    user.set_password(new_password)
    mark_token_used(db, reset_token.id)
    db.commit()
    
    return RedirectResponse(
        url=request.url_for("login") + "?status=password_reset",
        status_code=302
    )
```

### Step 7: Create Templates

Create `app/templates/auth/forgot_password.html` and `app/templates/auth/reset_password.html`

---

## 🔒 Security Best Practices

1. **Token Expiration**: 
   - Email tokens: 24 hours
   - SMS OTP: 15 minutes

2. **Rate Limiting**: 
   - Max 3 reset requests per hour per user
   - Max 5 OTP attempts before lockout

3. **Token Uniqueness**: 
   - Use cryptographically secure random tokens
   - Store hashed tokens in database

4. **Logging**: 
   - Log all password reset attempts
   - Alert on suspicious activity

5. **User Notification**: 
   - Send email/SMS when password is changed
   - Notify on successful reset

---

## 📱 Ghana-Specific Recommendations

1. **Use SMS as Primary Method**: Most users have phones, SMS is reliable
2. **AfricasTalking Integration**: Popular SMS gateway in Ghana
3. **Cost Consideration**: Budget for SMS costs (~0.05 GHS per SMS)
4. **Backup Method**: Provide email as fallback
5. **Local Phone Format**: Support +233 format (Ghana country code)

---

## ✅ Testing Checklist

- [ ] Request password reset via email
- [ ] Request password reset via SMS
- [ ] Verify token expiration
- [ ] Verify OTP expiration
- [ ] Test invalid tokens
- [ ] Test password strength requirements
- [ ] Test rate limiting
- [ ] Test concurrent requests
- [ ] Test email delivery
- [ ] Test SMS delivery

---

## 🚀 Quick Start

1. Run migration to create `password_reset_tokens` table
2. Configure email/SMS service credentials in `.env`
3. Add routes to `main.py`
4. Test with a test user account
5. Deploy and monitor

---

**Note**: This is a comprehensive guide. Implement incrementally, starting with email-based reset, then adding SMS support.

