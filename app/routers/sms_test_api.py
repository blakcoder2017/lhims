"""
SMS Test API Routes
For testing SMS functionality
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse
from app.core.templates import templates
from app.core.deps import role_required
from app.services.sms_onlinegh_service import sms_service, send_personalized_sms_notification

router = APIRouter(
    prefix="/api/v1/sms",
    tags=["SMS Testing"]
)


@router.get("/test", name="test_sms_page")
def test_sms_page(
    request: Request,
    current_user = Depends(role_required(["Admin"]))
):
    """SMS Test Page - Admin only"""
    context = {
        "request": request,
        "title": "SMS Test",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "api_key_configured": bool(sms_service.api_key),
        "sender": sms_service.sender
    }
    return templates.TemplateResponse("admin/sms_test.html", context)


@router.post("/test", name="test_sms")
def test_sms(
    request: Request,
    phone_number: str = Query(..., description="Phone number to test (e.g., +233594836357)"),
    message: str = Query("Test SMS from LHIMS", description="Test message to send"),
    current_user = Depends(role_required(["Admin"]))
):
    """
    Test SMS sending functionality.
    Admin only - for testing SMS integration.
    """
    try:
        result = sms_service.send_simple_sms(phone_number, message)
        
        if result.get("success"):
            response_data = result.get("response", {})
            handshake = response_data.get("handshake", {})
            
            # Check for specific error codes
            if handshake.get("label") == "MV_ERR_SENDER":
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Sender name not approved",
                        "error": "The sender name must be registered and approved with SMSOnlineGH",
                        "sender": sms_service.sender,
                        "handshake": handshake,
                        "phone_number": phone_number
                    }
                )
            elif handshake.get("label") == "HSHK_OK":
                return JSONResponse(content={
                    "status": "success",
                    "message": "SMS sent successfully",
                    "phone_number": phone_number,
                    "response": response_data
                })
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "warning",
                        "message": f"Unexpected response: {handshake.get('label')}",
                        "handshake": handshake,
                        "phone_number": phone_number
                    }
                )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to send SMS",
                    "error": result.get("error"),
                    "phone_number": phone_number
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing SMS: {str(e)}")


@router.post("/test-personalized", name="test_personalized_sms")
def test_personalized_sms(
    phone_number: str = Query(..., description="Phone number to test"),
    name: str = Query("Test User", description="Name for personalized message"),
    current_user = Depends(role_required(["Admin"]))
):
    """
    Test personalized SMS sending functionality.
    Admin only - for testing SMS integration with personalized messaging.
    """
    try:
        message_template = "Hello {$name}. This is a test SMS from LHIMS. Your appointment is scheduled for {$date} at {$department}."
        destinations = [{
            "number": phone_number,
            "values": [name, "2024-12-25 at 10:00", "General Medicine"]
        }]
        
        result = sms_service.send_personalized_sms(message_template, destinations)
        
        if result.get("success"):
            response_data = result.get("response", {})
            handshake = response_data.get("handshake", {})
            
            if handshake.get("label") == "MV_ERR_SENDER":
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Sender name not approved",
                        "error": "The sender name must be registered and approved with SMSOnlineGH",
                        "sender": sms_service.sender
                    }
                )
            elif handshake.get("label") == "HSHK_OK":
                return JSONResponse(content={
                    "status": "success",
                    "message": "Personalized SMS sent successfully",
                    "phone_number": phone_number,
                    "template": message_template,
                    "values": [name, "2024-12-25 at 10:00", "General Medicine"],
                    "response": response_data
                })
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "warning",
                        "message": f"Unexpected response: {handshake.get('label')}",
                        "handshake": handshake
                    }
                )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": "Failed to send personalized SMS",
                    "error": result.get("error"),
                    "phone_number": phone_number
                }
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing personalized SMS: {str(e)}")
