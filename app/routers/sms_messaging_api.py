"""
SMS Messaging API – send messages to clients or staff (festive, birthday, alerts, custom).
Admin only. Sends only to valid Ghana mobile numbers.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from app.core.templates import templates
from sqlalchemy.orm import Session

from app.core.deps import get_db, role_required
from app.models.user_models import User
from app.models.patient_models import Patient
from app.models.user_models import Role
from app.services.sms_onlinegh_service import is_valid_phone, send_sms_notification, sms_service

router = APIRouter(prefix="", tags=["SMS Messaging"])


def _collect_phones_for_audience(
    db: Session,
    audience: str,
    role_id: Optional[int] = None,
    custom_numbers: Optional[str] = None,
) -> List[str]:
    """Return list of valid Ghana phone numbers for the chosen audience."""
    phones: List[str] = []
    seen = set()

    if audience == "patients_with_phone":
        patients = db.query(Patient).filter(Patient.phone_number.isnot(None)).all()
        for p in patients:
            if p.phone_number and is_valid_phone(p.phone_number):
                n = p.phone_number.strip()
                if n not in seen:
                    seen.add(n)
                    phones.append(n)

    elif audience == "staff_by_role":
        if role_id is not None:
            users = db.query(User).filter(
                User.role_id == role_id,
                User.is_active == True,
                User.phone_number.isnot(None),
            ).all()
        else:
            users = db.query(User).filter(
                User.is_active == True,
                User.phone_number.isnot(None),
            ).all()
        for u in users:
            if u.phone_number and is_valid_phone(u.phone_number):
                n = u.phone_number.strip()
                if n not in seen:
                    seen.add(n)
                    phones.append(n)

    elif audience == "custom" and custom_numbers:
        for line in custom_numbers.strip().splitlines():
            for part in line.replace(",", " ").split():
                n = part.strip()
                if n and is_valid_phone(n) and n not in seen:
                    seen.add(n)
                    phones.append(n)

    return phones


@router.get("/admin/sms/messaging", name="sms_messaging_page")
def sms_messaging_page(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
):
    """SMS Messaging page: send to clients or staff (festive, birthday, alerts, custom)."""
    roles = db.query(Role).order_by(Role.name).all()
    context = {
        "request": request,
        "title": "SMS Messaging",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "roles": roles,
        "api_key_configured": bool(sms_service.api_key),
        "sender": sms_service.sender,
    }
    return templates.TemplateResponse("admin/sms_messaging.html", context)


@router.post("/admin/sms/messaging/send", name="sms_messaging_send", status_code=302)
def sms_messaging_send(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(role_required(["Admin"])),
    audience: str = Form(...),
    message_type: str = Form("custom"),
    custom_message: Optional[str] = Form(None),
    role_id: Optional[str] = Form(None),
    custom_numbers: Optional[str] = Form(None),
):
    """Send SMS to selected audience. Only valid Ghana numbers are used."""
    # Resolve role_id for staff_by_role
    role_id_int = None
    if audience == "staff_by_role" and role_id:
        try:
            role_id_int = int(role_id)
        except ValueError:
            role_id_int = None

    # Build message from type or custom
    message = (custom_message or "").strip()
    if not message and message_type != "custom":
        if message_type == "festive":
            message = "Season's greetings from LHIMS! We wish you good health and happiness. Thank you for choosing us."
        elif message_type == "birthday":
            message = "Happy Birthday from LHIMS! We wish you good health and a wonderful year ahead."
        elif message_type == "alert":
            message = "LHIMS: Important update. Please contact the hospital if you have any questions."
        else:
            message = "LHIMS: Thank you for being with us."

    if not message:
        from urllib.parse import urlencode
        base = str(request.url_for("sms_messaging_page"))
        return RedirectResponse(f"{base}?error=message_required", status_code=302)

    phones = _collect_phones_for_audience(db, audience, role_id_int, custom_numbers)
    sent = 0
    failed = 0
    for phone in phones:
        if send_sms_notification(phone, message):
            sent += 1
        else:
            failed += 1

    from urllib.parse import urlencode
    base = str(request.url_for("sms_messaging_page"))
    params = urlencode({"sent": sent, "failed": failed, "total": len(phones)})
    return RedirectResponse(f"{base}?{params}", status_code=302)
