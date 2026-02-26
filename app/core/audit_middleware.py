"""
Audit logging middleware for tracking user actions.
"""
from fastapi import Request, status
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.audit_models import AuditLog, AuditAction
from app.schemas.audit_schemas import AuditLogCreate
from datetime import datetime
import json


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests for audit purposes"""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Skip logging for static files and certain paths
        skip_paths = ['/static', '/favicon.ico', '/health']
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)
        
        # Get user from request state (set by auth middleware)
        user = getattr(request.state, 'user', None)
        user_id = user.id if user else None
        username = user.username if user else None
        
        # Get client IP
        ip_address = request.client.host if request.client else None
        
        # Get user agent
        user_agent = request.headers.get('user-agent', '')
        
        # Determine action type from HTTP method
        action_map = {
            'GET': AuditAction.VIEW,
            'POST': AuditAction.CREATE,
            'PUT': AuditAction.UPDATE,
            'PATCH': AuditAction.UPDATE,
            'DELETE': AuditAction.DELETE
        }
        action = action_map.get(request.method, AuditAction.VIEW)
        
        # Determine resource type from path
        resource_type = None
        if '/patients/' in request.url.path:
            resource_type = 'Patient'
        elif '/invoices/' in request.url.path:
            resource_type = 'Invoice'
        elif '/prescriptions/' in request.url.path:
            resource_type = 'Prescription'
        elif '/api/v1/ancillary/lab/orders/' in request.url.path:
            resource_type = 'LabOrder'
        elif '/api/v1/ancillary/radiology/orders/' in request.url.path:
            resource_type = 'RadiologyOrder'
        
        # Execute request
        start_time = datetime.now()
        response = await call_next(request)
        end_time = datetime.now()
        
        # Log the action (only for authenticated users and important actions)
        if user_id and action in [AuditAction.CREATE, AuditAction.UPDATE, AuditAction.DELETE]:
            try:
                db = SessionLocal()
                audit_data = AuditLogCreate(
                    user_id=user_id,
                    username=username,
                    action=action,
                    resource_type=resource_type,
                    ip_address=ip_address,
                    user_agent=user_agent[:500],  # Limit length
                    request_method=request.method,
                    request_path=request.url.path[:500],  # Limit length
                    status='success' if response.status_code < 400 else 'failed',
                    description=f"{request.method} {request.url.path}"
                )
                from app.crud import audit_crud
                audit_crud.create_audit_log(db, audit_data)
                db.close()
            except Exception as e:
                # Don't fail the request if audit logging fails
                print(f"Audit logging error: {e}")
        
        return response

