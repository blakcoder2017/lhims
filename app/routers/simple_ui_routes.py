"""
Simple UI Redirect Routes

This module provides simple redirect routes for common UI paths
to improve user experience and make the application more intuitive.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from app.core.templates import templates

router = APIRouter()

@router.get("/admin")
async def admin_redirect():
    """Redirect to admin users page"""
    return RedirectResponse(url="/admin/users", status_code=302)

@router.get("/patients")
async def patients_redirect():
    """Redirect to patients list page"""
    return RedirectResponse(url="/patients/list", status_code=302)

@router.get("/billing")
async def billing_redirect():
    """Redirect to billing invoices page"""
    return RedirectResponse(url="/billing/invoices", status_code=302)

@router.get("/triage")
async def triage_redirect():
    """Redirect to nurse triage queue"""
    return RedirectResponse(url="/nurse/triage-queue", status_code=302)

@router.get("/opd")
async def opd_redirect():
    """Redirect to OPD dashboard"""
    return RedirectResponse(url="/opd/dashboard", status_code=302)

@router.get("/ipd")
async def ipd_redirect():
    """Redirect to IPD dashboard"""
    return RedirectResponse(url="/ipd/dashboard", status_code=302)

@router.get("/emergency")
async def emergency_redirect():
    """Redirect to emergency dashboard"""
    return RedirectResponse(url="/emergency/dashboard", status_code=302)

@router.get("/reports/patient")
async def reports_patient_redirect():
    """Redirect to patient demographics reports"""
    return RedirectResponse(url="/reports/patients/demographics", status_code=302)

@router.get("/reports/clinical")
async def reports_clinical_redirect():
    """Redirect to clinical reports"""
    return RedirectResponse(url="/reports/opd/detailed", status_code=302)

@router.get("/wards")
async def wards_redirect():
    """Redirect to IPD wards management"""
    return RedirectResponse(url="/ipd/wards", status_code=302)

@router.get("/beds")
async def beds_redirect():
    """Redirect to IPD beds management"""
    return RedirectResponse(url="/ipd/beds", status_code=302)

@router.get("/patients/{patient_id}/pay")
async def patient_pay_redirect(patient_id: int):
    """Redirect to patient payment selection"""
    return RedirectResponse(url=f"/patients/{patient_id}/pay/consultation", status_code=302)

@router.get("/radiology/studies")
async def radiology_studies_redirect():
    """Redirect to radiology main page"""
    return RedirectResponse(url="/radiology", status_code=302)

@router.get("/radiology")
async def radiology_redirect():
    """Redirect to radiology dashboard"""
    return RedirectResponse(url="/api/v1/ancillary/radiology", status_code=302)
