#!/usr/bin/env python3
"""
Quick SMS Test Script
Tests SMS sending to a phone number
"""
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.sms_onlinegh_service import sms_service

def test_sms(phone_number: str, message: str = "Test SMS from LHIMS"):
    """Test sending SMS"""
    print(f"Testing SMS to: {phone_number}")
    print(f"Message: {message}")
    print(f"API Key configured: {'Yes' if sms_service.api_key else 'No'}")
    print(f"Sender: {sms_service.sender}")
    print("-" * 50)
    
    result = sms_service.send_simple_sms(phone_number, message)
    
    print(f"\nResult:")
    print(f"Success: {result.get('success')}")
    
    if result.get('response'):
        print(f"Response: {result.get('response')}")
    
    if result.get('error'):
        print(f"Error: {result.get('error')}")
    
    # Check for specific error codes
    if result.get('response'):
        handshake = result.get('response', {}).get('handshake', {})
        if handshake.get('label') == 'MV_ERR_SENDER':
            print("\n⚠️  ERROR: Sender name not approved!")
            print("   The sender name must be registered and approved with SMSOnlineGH.")
            print(f"   Current sender: {sms_service.sender}")
            print("   Please contact SMSOnlineGH to register/approve your sender name.")
        elif handshake.get('label') == 'HSHK_OK':
            print("\n✅ SMS sent successfully!")
            if result.get('response', {}).get('data'):
                print(f"   Batch ID: {result.get('response', {}).get('data', {}).get('batch')}")
        else:
            print(f"\n⚠️  Response: {handshake.get('label')} (ID: {handshake.get('id')})")
    
    return result

if __name__ == "__main__":
    phone_number = "+233594836357"
    message = "Test SMS from LHIMS - This is a test message to verify SMS integration."
    
    if len(sys.argv) > 1:
        phone_number = sys.argv[1]
    if len(sys.argv) > 2:
        message = " ".join(sys.argv[2:])
    
    test_sms(phone_number, message)
