from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from fastapi.exceptions import RequestValidationError, HTTPException as StarletteHTTPException
from jinja2.exceptions import TemplateNotFound
from urllib.parse import urlparse, parse_qs, urlencode, urljoin
from datetime import date
import os


def calculate_age(dob):
    """Calculate age from date of birth."""
    if not dob:
        return None
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


app = FastAPI(title=f"{settings.app_title}")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Use shared templates from app.core.templates (includes age filter registration)
from app.core.templates import templates

# --- ROUTER IMPORTS ---
# 1. Auth/API Token Routers (Includes /api/v1/auth/token)
from app.routers.auth import router as auth_router, ui_router as auth_ui_router 
# 2. UI Dashboard Router (CRITICAL: Contains the GET / route)
from app.routers import ui_routes 
# 3. Other API/UI Routers
from app.routers import patient_api
from app.routers import triage_api
from app.routers import ipd_api
from app.routers import ipd_ui_routes
from app.routers import opd_api
from app.routers import opd_ui_routes
from app.routers import nurse_api
from app.routers import doctor_api
from app.routers import insurance_provider_api
from app.routers import insurance_provider_ui_routes
from app.routers import doctor_list_api
from app.routers import ward_type_api
from app.routers import ward_type_ui_routes
from app.routers import payment_ui_routes
from app.routers import reports_api
from app.routers import expense_api
from app.routers import procedure_api
from app.routers import procedure_catalog_api
from app.routers import department_api
from app.routers import shift_type_api
from app.routers import bed_type_api
from app.routers import bed_type_ui_routes


# Uploads directory - persists in Docker via ./uploads volume
PROJECT_ROOT = os.path.dirname(BASE_DIR)
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")

# Serve legacy logo URLs (/static/uploads/logos/...) from uploads dir for backward compatibility
from fastapi.responses import FileResponse
@app.get("/static/uploads/logos/{filename:path}")
def serve_legacy_logo(filename: str):
    filepath = os.path.join(UPLOADS_DIR, "logos", filename)
    if os.path.isfile(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="Not found")

# Mount static files directory
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Mount uploads directory (hospital logos, etc.)
if os.path.isdir(UPLOADS_DIR):
    app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# =======================================================
# === EXCEPTION HANDLERS (CRITICAL FOR AUTH REDIRECTS) ===
# =======================================================

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    # Helper function to get current user and role name if available
    def get_current_user_from_request():
        """Try to get current user from request state or cookie, returns (user, role_name)"""
        try:
            # Try to get from request state (set by middleware)
            if hasattr(request.state, 'user') and request.state.user:
                user = request.state.user
                # Try to get role name, handle detached instance
                try:
                    role_name = user.role.name if user.role else None
                except:
                    role_name = None
                return user, role_name
            
            # Try to get from cookie and verify token
            from app.core.security import verify_access_token
            from app.db.database import SessionLocal
            from app.models.user_models import User
            from sqlalchemy.orm import joinedload
            from fastapi import HTTPException, status
            
            access_token = request.cookies.get("access_token")
            if access_token:
                db = SessionLocal()
                try:
                    credentials_exception = HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Could not validate credentials",
                    )
                    token_data = verify_access_token(access_token, credentials_exception)
                    # Eagerly load the role relationship to avoid DetachedInstanceError
                    user = db.query(User).options(joinedload(User.role)).filter(User.id == token_data.id).first()
                    if user and user.is_active:
                        # Get role name while session is still open
                        role_name = user.role.name if user.role else None
                        # Store role name as a simple attribute to avoid detached instance issues
                        user._role_name = role_name
                        return user, role_name
                except:
                    return None, None
                finally:
                    db.close()
        except:
            pass
        return None, None
    
    # Get current user and role name if available
    current_user, user_role = get_current_user_from_request()
    
    # --- 1. Handle 401 Unauthorized -> Redirect to Login ---
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        # Check if the request is for a UI path (not starting with /api/)
        if not request.url.path.startswith("/api/"):
            # Redirect to the login page, preserving the original URL
            from urllib.parse import urlencode
            login_url = request.url_for("login")
            # Build the redirect URL with the original path as 'next' parameter
            redirect_params = urlencode({"next": str(request.url)})
            full_redirect_url = f"{login_url}?{redirect_params}"
            return RedirectResponse(full_redirect_url, status_code=status.HTTP_302_FOUND)
        
        # If it's an API call, return standard JSON 401
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required. Please check your token."}
        )

    # --- 2. Handle 403 Forbidden -> Show user-friendly error page ---
    if exc.status_code == status.HTTP_403_FORBIDDEN:
        if not request.url.path.startswith("/api/"):
            # Extract role information from error detail if available
            error_message = exc.detail if exc.detail else "Access forbidden"
            required_roles = None
            parsed_user_role = user_role  # Use the role from get_current_user_from_request
            
            if error_message and "User role" in error_message and "Required roles" in error_message:
                # Parse the error message to extract role information
                import re
                role_match = re.search(r"User role '([^']+)'", error_message)
                required_match = re.search(r"Required roles: (.+)", error_message)
                if role_match:
                    parsed_user_role = role_match.group(1)
                if required_match:
                    required_roles = required_match.group(1)
            
            # Ensure we have safe defaults for template context
            safe_user_role = parsed_user_role or user_role or "Guest"
            safe_context = {
                "request": request,
                "status_code": 403,
                "detail": error_message,
                "current_user": current_user if current_user else None,
                "user_role": safe_user_role,
                "required_roles": required_roles
            }
            
            try:
                return templates.TemplateResponse(
                    "error_403.html",
                    safe_context,
                    status_code=403
                )
            except Exception as template_error:
                # Fallback if template rendering fails
                import traceback
                print(f"[ERROR] Failed to render error_403.html: {template_error}")
                print(traceback.format_exc())
                # Try to return a simple HTML response instead
                from fastapi.responses import HTMLResponse
                return HTMLResponse(
                    content=f"""
                    <html>
                        <head><title>Access Denied</title></head>
                        <body>
                            <h1>403 - Access Denied</h1>
                            <p>You do not have permission to access this resource.</p>
                            <p><strong>Your Role:</strong> {safe_user_role}</p>
                            {f'<p><strong>Required Roles:</strong> {required_roles}</p>' if required_roles else ''}
                            <p><a href="/">Return to Dashboard</a> | <a href="/login">Login</a></p>
                        </body>
                    </html>
                    """,
                    status_code=403
                )
    
    # --- 3. Handle 404 Not Found -> Show user-friendly error page ---
    if exc.status_code == status.HTTP_404_NOT_FOUND:
        if not request.url.path.startswith("/api/"):
            # Ensure we have safe defaults for template context
            safe_context = {
                "request": request,
                "status_code": 404,
                "module_name": request.url.path,
                "reason": "The requested page or module is not available.",
                "current_user": current_user if current_user else None,
                "user_role": user_role if user_role else "Guest",
                "detail": str(exc.detail) if exc.detail else "The requested resource was not found."
            }
            
            # Only show "module unavailable" for actual template errors, not resource not found errors
            if "TemplateNotFound" in str(exc.detail):
                try:
                    return templates.TemplateResponse(
                        "module_unavailable.html",
                        safe_context,
                        status_code=404
                    )
                except Exception as template_error:
                    print(f"[ERROR] Failed to render module_unavailable.html: {template_error}")
                    return HTMLResponse(
                        content=f"""
                        <html>
                            <head><title>Module Unavailable</title></head>
                            <body>
                                <h1>Module Unavailable</h1>
                                <p>The requested module or feature is currently not available.</p>
                                <p><strong>Module:</strong> {safe_context['module_name']}</p>
                                <p><a href="/">Return to Dashboard</a> | <a href="/login">Login</a></p>
                            </body>
                        </html>
                        """,
                        status_code=404
                    )
            
            # For resource not found errors (e.g., "Ward type not found", "Patient not found"), show regular error page
            try:
                return templates.TemplateResponse(
                    "error.html", 
                    safe_context,
                    status_code=404
                )
            except Exception as template_error:
                print(f"[ERROR] Failed to render error.html for 404: {template_error}")
                return HTMLResponse(
                    content=f"""
                    <html>
                        <head><title>Not Found</title></head>
                        <body>
                            <h1>404 - Not Found</h1>
                            <p>{safe_context['detail']}</p>
                            <p><a href="/">Return to Dashboard</a> | <a href="/login">Login</a></p>
                        </body>
                    </html>
                    """,
                    status_code=404
                )
        return JSONResponse(status_code=404, content={"detail": exc.detail})
    
    # --- 4. Handle Other HTTP Exceptions (e.g., 500, 404) ---
    # Render an error template for UI routes
    if not request.url.path.startswith("/api/"):
        # Ensure we have safe defaults for template context
        safe_context = {
            "request": request,
            "status_code": exc.status_code,
            "detail": str(exc.detail) if exc.detail else "An error occurred",
            "current_user": current_user if current_user else None,
            "user_role": user_role if user_role else "Guest"
        }
        
        try:
            return templates.TemplateResponse(
                "error.html", 
                safe_context,
                status_code=exc.status_code
            )
        except Exception as template_error:
            # If template rendering fails, return a simple HTML response
            import traceback
            print(f"[ERROR] Failed to render error.html: {template_error}")
            print(traceback.format_exc())
            return HTMLResponse(
                content=f"""
                <html>
                    <head><title>Error {exc.status_code}</title></head>
                    <body>
                        <h1>Error {exc.status_code}</h1>
                        <p>{safe_context['detail']}</p>
                        <p><a href="/login">Return to Login</a></p>
                    </body>
                </html>
                """,
                status_code=exc.status_code
            )
    
    # Fallback for other API errors
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Enhanced handler for Pydantic Validation Errors (Status 422)"""
    from typing import List, Dict, Any
    from app.core.validation import create_error_response, format_validation_errors
    
    def sanitize_errors(errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert bytes to strings in error details for JSON serialization"""
        sanitized = []
        for error in errors:
            clean = {}
            for key, value in error.items():
                if isinstance(value, bytes):
                    clean[key] = value.decode('utf-8', errors='replace')
                elif isinstance(value, (list, tuple)):
                    clean[key] = [v.decode('utf-8', errors='replace') if isinstance(v, bytes) else v for v in value]
                else:
                    clean[key] = value
            sanitized.append(clean)
        return sanitized
    
    # For API requests, return JSON
    if request.url.path.startswith("/api/"):
        sanitized_errors = sanitize_errors(exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": sanitized_errors,
                "message": format_validation_errors(sanitized_errors)
            }, 
        )
    
    # For UI requests (form submissions), redirect with error message
    # Try to get the referer or default to dashboard
    referer = request.headers.get("referer", "/")
    error_message = format_validation_errors(exc.errors())
    
    # If referer is a form page, redirect back with error
    if any(path in referer for path in ["/register", "/create", "/add", "/update"]):
        from urllib.parse import quote, urlparse, parse_qs, urlencode, urljoin
        encoded_error = quote(error_message[:200])  # Limit length
        
        # Parse the referer URL to properly handle query parameters
        parsed = urlparse(referer)
        query_params = parse_qs(parsed.query)
        query_params['error'] = [encoded_error]
        
        # Reconstruct URL with proper query string
        new_query = urlencode(query_params, doseq=True)
        redirect_url = urljoin(referer, f"{parsed.path}?{new_query}")
        
        return RedirectResponse(url=redirect_url, status_code=302)
    
    # Otherwise, show error page
    return create_error_response(
        request,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "Validation Error",
        {"errors": exc.errors()}
    )

app.add_exception_handler(RequestValidationError, validation_exception_handler)

# Handle TemplateNotFound exceptions
@app.exception_handler(TemplateNotFound)
async def template_not_found_handler(request: Request, exc: TemplateNotFound):
    """Handle missing template errors gracefully"""
    if not request.url.path.startswith("/api/"):
        return templates.TemplateResponse(
            "module_unavailable.html",
            {
                "request": request,
                "status_code": 404,
                "module_name": exc.name if hasattr(exc, 'name') else request.url.path,
                "reason": f"The template '{exc.name if hasattr(exc, 'name') else 'requested'}' is not available. This module may still be under development."
            },
            status_code=404
        )
    return JSONResponse(
        status_code=404,
        content={"detail": f"Template not found: {exc.name if hasattr(exc, 'name') else 'unknown'}"}
    )

# We rely on @app.exception_handler(StarletteHTTPException) for all HTTP exceptions.


# =======================================================
# === ROUTER INCLUSION (Ensures all routes are linked) ===
# =======================================================

# 1. API Routers
app.include_router(auth_router)             # /api/v1/auth/token
app.include_router(triage_api.router)       # /triage routes

# 1. UI Routers (No prefix required)
app.include_router(ui_routes.router)        # CRITICAL: Includes the GET / dashboard route
app.include_router(auth_ui_router)          # /login, /logout
app.include_router(patient_api.router, prefix="", tags=["Patients"]) # /patient routes

# 1.5. Simple UI Redirect Routes
from app.routers import simple_ui_routes
app.include_router(simple_ui_routes.router, prefix="", tags=["Simple UI Redirects"])

# 3. Appointment & Queue Management Routers
from app.routers import appointment_api
app.include_router(appointment_api.router, prefix="", tags=["Appointments"]) # /appointment routes

# 4. Patient Records & Medical History Routers
from app.routers import patient_records_api
app.include_router(patient_records_api.router, prefix="", tags=["Patient Records"]) # /patients routes

# 5. Clinical Encounter & CPOE Routers
from app.routers import encounter_api
app.include_router(encounter_api.router)  # /api/v1/encounters routes
app.include_router(opd_api.router, prefix="", tags=["OPD"])  # /api/v1/opd-visits routes
app.include_router(opd_ui_routes.router, prefix="", tags=["OPD UI"])  # /opd/* UI routes for OPD management
from app.routers import emergency_ui_routes
app.include_router(emergency_ui_routes.router, prefix="", tags=["Emergency UI"])  # /emergency/* UI routes
from app.routers import midwife_antenatal_ui_routes
app.include_router(midwife_antenatal_ui_routes.router, prefix="", tags=["Midwife/Antenatal"])  # /midwife/* UI routes
from app.routers import antenatal_api
app.include_router(antenatal_api.router, prefix="", tags=["Antenatal API"])  # /api/v1/antenatal/* routes
from app.routers import birth_ui_routes
app.include_router(birth_ui_routes.router, prefix="", tags=["Births/Delivery"])  # /births/* UI routes
app.include_router(ipd_api.router, prefix="", tags=["IPD"])  # /api/v1/wards, /api/v1/beds, /api/v1/admissions, /api/v1/doctor-duties routes
app.include_router(ipd_ui_routes.router, prefix="", tags=["IPD UI"])  # /ipd/* UI routes for IPD management
from app.routers import drug_administration_api
app.include_router(drug_administration_api.router, tags=["Drug Administration"])  # /api/v1/drug_administrations routes
app.include_router(nurse_api.router, prefix="", tags=["Nurse"])  # /nurse/* routes for nurse dashboard and triage queue
app.include_router(doctor_api.router, prefix="", tags=["Doctor"])  # /doctor/* routes for doctor dashboard and queue
app.include_router(insurance_provider_api.router, tags=["Insurance Providers"])  # /api/v1/insurance-providers routes
app.include_router(insurance_provider_ui_routes.router, prefix="", tags=["Insurance Providers UI"])  # /insurance-providers/* UI routes
app.include_router(doctor_list_api.router, prefix="", tags=["Doctors"])  # /doctors/list routes
app.include_router(ward_type_api.router, tags=["Ward Types"])  # /api/v1/ward-types routes
app.include_router(ward_type_ui_routes.router, prefix="", tags=["Ward Types UI"])  # /admin/ward-types/* UI routes

# 6. Ancillary Services Routers (Lab, Radiology, Pharmacy)
from app.routers import ancillary_services_api
app.include_router(ancillary_services_api.router, prefix="/api/v1/ancillary", tags=["Ancillary Services"])  # /api/v1/ancillary/lab, /api/v1/ancillary/radiology, /api/v1/ancillary/pharmacy routes

# 7. Billing & Payment Routers
from app.routers import billing_api
app.include_router(billing_api.router, prefix="", tags=["Billing"])  # /billing routes
app.include_router(payment_ui_routes.router, prefix="", tags=["Payment UI"])  # /patients/{patient_id}/pay/* routes

# 7a. Consolidated Receipt Routers
from app.routers import consolidated_receipt_api
app.include_router(consolidated_receipt_api.router, prefix="", tags=["Consolidated Receipts"])  # /billing/consolidated routes

# 8. Appointments Management Routers
from app.routers import scheduled_appointment_api, appointments_ui_routes, queue_api
app.include_router(scheduled_appointment_api.router, prefix="", tags=["Scheduled Appointments"])  # /api/v1/appointments routes
app.include_router(appointments_ui_routes.router, prefix="", tags=["Appointments UI"])  # /appointments routes
app.include_router(queue_api.router, prefix="", tags=["OPD Queue"])  # /api/v1/queue routes

# 9. Reports & Analytics Routers
from app.routers import reports_api
app.include_router(reports_api.router, prefix="", tags=["Reports"])  # /reports routes

# 9. Expense Management Routers
app.include_router(expense_api.router, prefix="", tags=["Expenses"])  # /expenses routes

# 10. Procedure Management Routers
# IMPORTANT: Include catalog routes BEFORE procedure routes to avoid route conflicts
# (catalog routes are literal paths like /procedures/catalog, procedure routes have path params like /procedures/{id})
app.include_router(procedure_catalog_api.router, prefix="", tags=["Procedure Catalog"])  # /procedures/catalog routes
app.include_router(procedure_api.router, prefix="", tags=["Procedures"])  # /procedures routes

# 11. Department Management Routers
app.include_router(department_api.router, prefix="", tags=["Departments"])  # /admin/departments routes

# 12. Shift Type Management Routers
app.include_router(shift_type_api.router, prefix="", tags=["Shift Types"])  # /admin/shift-types routes

# 13. Bed Type Management Routers
app.include_router(bed_type_api.router, prefix="", tags=["Bed Types"])  # /api/v1/bed-types routes
app.include_router(bed_type_ui_routes.router, prefix="", tags=["Bed Types UI"])  # /admin/bed-types routes

# 9. Inventory Management Routers
from app.routers import inventory_api
app.include_router(inventory_api.router, prefix="", tags=["Inventory"])  # /pharmacy/inventory routes

# 10. Lab Sample Tracking & QC Routers
from app.routers import lab_tracking_api
app.include_router(lab_tracking_api.router, prefix="", tags=["Lab Tracking"])  # /lab/samples, /lab/qc routes

# 11. Formulary & Drug Interactions Management Routers
from app.routers import formulary_api
app.include_router(formulary_api.router, prefix="", tags=["Formulary"])  # /pharmacy/formulary, /pharmacy/drug-interactions routes

# 11a. Pharmacy Ghana-Ready API (formulary search, stock-in, FEFO, interactions)
from app.routers import pharmacy_ghana_api
app.include_router(pharmacy_ghana_api.router, prefix="/api/v1", tags=["Pharmacy Ghana"])  # /api/v1/pharmacy/formulary/search, etc.

# 11b. Pharmacy Ghana UI (drug catalogue, batches, reports)
from app.routers import pharmacy_ghana_ui_routes
app.include_router(pharmacy_ghana_ui_routes.router, prefix="", tags=["Pharmacy Ghana UI"])

# 12. Lab Test Catalog Routers
from app.routers import lab_catalog_api
app.include_router(lab_catalog_api.router, prefix="", tags=["Lab Catalog"])  # /lab/tests, /lab/reference-ranges routes

# 12a. Lab Template Management (Admin)
from app.routers import lab_template_api
app.include_router(lab_template_api.router, prefix="", tags=["Lab Templates"])  # /lab/templates routes

# 12b. Lab Reference Range Audit (Read-only diagnostics)
from app.routers import lab_reference_range_audit_api
app.include_router(lab_reference_range_audit_api.router, prefix="", tags=["Lab Reference Range Audit"])  # /lab/audit routes

# 12c. Lab Demo (Development Testing)
from app.routers import lab_demo_api
app.include_router(lab_demo_api.router, prefix="", tags=["Lab Demo"])  # /lab/demo routes

# 12c. Lab Inventory Management (Equipment & Reagents)
from app.routers import lab_inventory_api
app.include_router(lab_inventory_api.router, prefix="", tags=["Lab Inventory"])  # /lab/inventory routes

# 12d. Lab Unified Operations (Reference Range Engine, Result Interpretation)
from app.routers import lab_merge_api
app.include_router(lab_merge_api.router, prefix="", tags=["Lab - Unified Operations"])  # /lab/reference-ranges/lookup, /lab/results/interpret, /lab/tests/merge routes

# 13. Supplier Management Routers
from app.routers import supplier_api
app.include_router(supplier_api.router, prefix="", tags=["Suppliers"])  # /pharmacy/suppliers routes

# 14. Admin & System Management Routers
from app.routers import admin_api
app.include_router(admin_api.router, prefix="", tags=["Admin"])  # /admin routes

# 14a. Service Pricing Management Routers
from app.routers import service_pricing_api
from app.routers import disease_api
app.include_router(service_pricing_api.router, prefix="", tags=["Service Pricing"])  # /admin/service-pricing routes

# 14c. Disease Management Routers
app.include_router(disease_api.router, prefix="", tags=["Diseases"])  # /admin/diseases routes

# 14b. Role Permissions Management Routers
from app.routers import role_permissions_api
app.include_router(role_permissions_api.router, prefix="", tags=["Role Permissions"])  # /admin/roles/permissions routes

# 15. Radiology Scheduling Routers
from app.routers import radiology_scheduling_api
app.include_router(radiology_scheduling_api.router, prefix="", tags=["Radiology Scheduling"])  # /radiology/schedule routes

# 16. NHIS Claims Routers
from app.routers import claims_api
app.include_router(claims_api.router, prefix="", tags=["NHIS Claims"])  # /claims routes

# 16a. SMS Test Routers (Admin only)
from app.routers import sms_test_api
app.include_router(sms_test_api.router, prefix="", tags=["SMS Testing"])

# 16b. SMS Messaging (Admin only – clients/staff messaging)
from app.routers import sms_messaging_api
app.include_router(sms_messaging_api.router, prefix="", tags=["SMS Messaging"])

# 17. Backup & Recovery Routers
from app.routers import backup_api
app.include_router(backup_api.router, prefix="", tags=["Backup"])  # /admin/backup routes

# 18. PACS (Picture Archiving and Communication System) Routers
from app.routers import pacs_api
app.include_router(pacs_api.router, prefix="", tags=["PACS"])  # /pacs routes

# 19. User Profile Management Routers
from app.routers import profile_api
app.include_router(profile_api.router, prefix="", tags=["Profile"])  # /profile routes

# 20. Password Reset Routers
from app.routers import password_reset_api
app.include_router(password_reset_api.router, prefix="", tags=["Password Reset"])  # /forgot-password, /reset-password routes

# 21. Walk-in Orders Management Routers
from app.routers import walk_in_orders_api
app.include_router(walk_in_orders_api.router, prefix="", tags=["Walk-in Orders"])  # /walk-in-orders routes

# 22. Direct Service Requests from Patient Profile
from app.routers import direct_service_requests_api
app.include_router(direct_service_requests_api.router, prefix="", tags=["Direct Service Requests"])  # /patients/{id}/direct-requests routes

from app.routers import direct_service_registration_api
app.include_router(direct_service_registration_api.router, prefix="", tags=["Direct Service Registration"])  # /direct-service-registration routes

# Debug Router for testing permissions
from app.routers import debug_permissions_api
app.include_router(debug_permissions_api.router, prefix="", tags=["Debug"])  # /debug/my-permissions

# =======================================================
# DHIMS2 Integration Router
# =======================================================
from app.integrations.dhims2 import router as dhims2_router
app.include_router(dhims2_router.router, prefix="", tags=["DHIMS2 Integration"])  # /api/dhims2 routes
# =======================================================
# === Health Check Endpoint (for Docker) ===
# =======================================================

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    """Avoid 404 for favicon requests - return 204 No Content."""
    from fastapi.responses import Response
    return Response(status_code=204)

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for Docker and load balancer health checks."""
    return {
        "status": "healthy",
        "app": settings.app_title,
        "version": settings.version
    }
