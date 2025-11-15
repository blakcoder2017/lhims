"""
SMS Service for sending password reset OTPs
Supports multiple SMS gateways suitable for Ghana context
"""
import os
from typing import Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# SMS Configuration
AFRICASTALKING_API_KEY = os.getenv("AFRICASTALKING_API_KEY", "")
AFRICASTALKING_USERNAME = os.getenv("AFRICASTALKING_USERNAME", "")
AFRICASTALKING_SENDER_ID = os.getenv("AFRICASTALKING_SENDER_ID", "LHIMS")

# Alternative: Twilio (if needed)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")


def send_sms_otp_africastalking(phone_number: str, otp: str, user_name: Optional[str] = None) -> bool:
    """
    Send SMS OTP using AfricasTalking API (Recommended for Ghana)
    
    Returns True if sent successfully, False otherwise
    """
    if not REQUESTS_AVAILABLE:
        print(f"WARNING: requests library not installed. Install with: pip install requests")
        print(f"Would send OTP to {phone_number}: {otp}")
        return False
    
    if not AFRICASTALKING_API_KEY or not AFRICASTALKING_USERNAME:
        # Log warning: SMS not configured
        print(f"WARNING: AfricasTalking not configured. Would send OTP to {phone_number}: {otp}")
        return False
    
    try:
        # Format phone number (ensure +233 format for Ghana)
        if phone_number.startswith("0"):
            phone_number = "+233" + phone_number[1:]
        elif not phone_number.startswith("+"):
            phone_number = "+233" + phone_number
        
        url = "https://api.africastalking.com/version1/messaging"
        headers = {
            "ApiKey": AFRICASTALKING_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        message = f"Your LHIMS password reset OTP is: {otp}. Valid for 15 minutes. Do not share this code."
        if user_name:
            message = f"Hello {user_name}, {message}"
        
        data = {
            "username": AFRICASTALKING_USERNAME,
            "to": phone_number,
            "message": message,
            "from": AFRICASTALKING_SENDER_ID
        }
        
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 201:
            return True
        else:
            print(f"AfricasTalking API error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending SMS via AfricasTalking: {e}")
        return False


def send_sms_otp_twilio(phone_number: str, otp: str, user_name: Optional[str] = None) -> bool:
    """
    Send SMS OTP using Twilio (Alternative)
    
    Returns True if sent successfully, False otherwise
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print(f"WARNING: Twilio not configured. Would send OTP to {phone_number}: {otp}")
        return False
    
    try:
        from twilio.rest import Client
        
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        message = f"Your LHIMS password reset OTP is: {otp}. Valid for 15 minutes."
        if user_name:
            message = f"Hello {user_name}, {message}"
        
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        return message.sid is not None
        
    except ImportError:
        print("WARNING: Twilio library not installed. Install with: pip install twilio")
        return False
    except Exception as e:
        print(f"Error sending SMS via Twilio: {e}")
        return False


def send_sms_otp(phone_number: str, otp: str, user_name: Optional[str] = None) -> bool:
    """
    Send SMS OTP using the configured SMS gateway
    
    Priority: AfricasTalking > Twilio
    
    Returns True if sent successfully, False otherwise
    """
    # Try AfricasTalking first (recommended for Ghana)
    if AFRICASTALKING_API_KEY and AFRICASTALKING_USERNAME:
        if send_sms_otp_africastalking(phone_number, otp, user_name):
            return True
    
    # Fallback to Twilio
    if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
        if send_sms_otp_twilio(phone_number, otp, user_name):
            return True
    
    # If neither is configured, log warning
    print(f"WARNING: No SMS gateway configured. OTP for {phone_number}: {otp}")
    return False

