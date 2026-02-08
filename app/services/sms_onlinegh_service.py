"""
SMS Service for SMSOnlineGH API
Supports personalized messaging using SMSOnlineGH HTTP REST API
"""
import os
import requests
from typing import List, Optional, Dict, Any
from datetime import datetime

# SMSOnlineGH Configuration
from app.core.config import settings

SMSONLINEGH_API_KEY = settings.SMSONLINEGH_API_KEY
SMSONLINEGH_SENDER = settings.SMSONLINEGH_SENDER
SMSONLINEGH_API_URL = "https://api.smsonlinegh.com/v5/message/sms/send"


class SMSOnlineGHService:
    """Service for sending SMS via SMSOnlineGH API"""
    
    def __init__(self):
        # Strip whitespace/quotes so .env values don't break auth (HSHK_ERR_UA_AUTH)
        self.api_key = (SMSONLINEGH_API_KEY or "").strip().strip('"').strip("'")
        self.sender = (SMSONLINEGH_SENDER or "LHIMS").strip().strip('"').strip("'")
        self.api_url = SMSONLINEGH_API_URL
    
    def format_phone_number(self, phone_number: str) -> str:
        """
        Format phone number to Ghana format (233XXXXXXXXX)
        Converts 0XXXXXXXXX or +233XXXXXXXXX to 233XXXXXXXXX
        """
        if not phone_number or not isinstance(phone_number, str):
            return ""
        phone_number = str(phone_number).strip()
        if not phone_number:
            return ""
        phone_number = phone_number.replace(" ", "").replace("-", "")
        if phone_number.startswith("+233"):
            phone_number = phone_number[1:]
        elif phone_number.startswith("0"):
            phone_number = "233" + phone_number[1:]
        elif not phone_number.startswith("233"):
            phone_number = "233" + phone_number if len(phone_number) == 9 else phone_number
        return phone_number if (len(phone_number) == 12 and phone_number.startswith("233") and phone_number[3:].isdigit()) else ""

    def is_valid_phone(self, phone_number: str) -> bool:
        """
        Return True if the number looks like a valid Ghana mobile (10 digits: 0XXXXXXXXX or 233XXXXXXXXX).
        Only sends SMS when this returns True.
        """
        formatted = self.format_phone_number(phone_number)
        if not formatted:
            return False
        return len(formatted) == 12 and formatted.startswith("233") and formatted[3:].isdigit()
    
    def send_personalized_sms(
        self,
        message_template: str,
        destinations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send personalized SMS to multiple destinations
        
        Args:
            message_template: Message template with variables like {$name}, {$balance}
            destinations: List of dicts with 'number' and 'values' keys
                Example: [
                    {"number": "0246314915", "values": ["Daniel", 560.45]},
                    {"number": "0242053072", "values": ["Emmanuel", 348.56]}
                ]
        
        Returns:
            Dict with 'success' (bool) and 'response' (dict) or 'error' (str)
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "SMSOnlineGH API key not configured"
            }
        
        if not destinations:
            return {
                "success": False,
                "error": "No destinations provided"
            }
        
        # Format destinations with proper phone numbers
        formatted_destinations = []
        for dest in destinations:
            phone_number = self.format_phone_number(dest.get("number", ""))
            if not phone_number:
                continue
            
            formatted_destinations.append({
                "number": phone_number,
                "values": dest.get("values", [])
            })
        
        if not formatted_destinations:
            return {
                "success": False,
                "error": "No valid phone numbers found"
            }
        
        # Prepare request payload
        payload = {
            "text": message_template,
            "type": 0,  # SMS type
            "sender": self.sender,
            "destinations": formatted_destinations
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"key {self.api_key}"
        }
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # SMSOnlineGH returns 200 but success is only when handshake.label == "HSHK_OK"
                # Other labels (e.g. MV_ERR_SENDER = sender not approved) mean the SMS was not accepted
                handshake = response_data.get("handshake") or {}
                label = handshake.get("label") if isinstance(handshake, dict) else None
                if label == "HSHK_OK":
                    return {
                        "success": True,
                        "response": response_data
                    }
                err_msg = f"API handshake label: {label} (expected HSHK_OK)"
                print(f"[SMSOnlineGH] {err_msg} handshake={handshake}")
                return {
                    "success": False,
                    "error": err_msg,
                    "response": response_data,
                    "handshake": handshake
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned status {response.status_code}: {response.text}"
                }
        
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def send_simple_sms(
        self,
        phone_number: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a simple SMS to a single recipient (non-personalized)
        
        Args:
            phone_number: Recipient phone number
            message: Message text
        
        Returns:
            Dict with 'success' (bool) and 'response' (dict) or 'error' (str)
        """
        return self.send_personalized_sms(
            message_template=message,
            destinations=[{"number": phone_number, "values": []}]
        )


# Global instance
sms_service = SMSOnlineGHService()


def is_valid_phone(phone_number: str) -> bool:
    """Return True if number is a valid Ghana mobile (only send SMS when this is True)."""
    return sms_service.is_valid_phone(phone_number or "")


def send_sms_notification(
    phone_number: str,
    message: str
) -> bool:
    """
    Convenience function to send SMS notification.
    Sends only if phone_number is valid (Ghana format).
    """
    if not is_valid_phone(phone_number or ""):
        return False
    result = sms_service.send_simple_sms(phone_number, message)
    return result.get("success", False)


def send_sms_if_valid(phone_number: str, message: str) -> bool:
    """
    Send SMS only when a valid phone number is provided.
    Returns True if sent successfully, False if invalid phone or send failed.
    """
    return send_sms_notification(phone_number or "", message)


def send_personalized_sms_notification(
    message_template: str,
    destinations: List[Dict[str, Any]]
) -> bool:
    """
    Convenience function to send personalized SMS notifications
    
    Args:
        message_template: Message template with variables
        destinations: List of destination dicts with 'number' and 'values'
    
    Returns:
        True if sent successfully, False otherwise
    """
    result = sms_service.send_personalized_sms(message_template, destinations)
    return result.get("success", False)
