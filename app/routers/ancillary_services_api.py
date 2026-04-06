from fastapi import APIRouter, Depends, status, HTTPException, Form, Request, Query, File, UploadFile
from fastapi.responses import RedirectResponse, Response
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, timedelta
import os
import uuid
import json

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.core.templates import templates
from app.models.encounter_models import LabOrder, RadiologyOrder, Prescription, OrderStatus, Encounter
from app.models.patient_models import Patient
from app.crud import encounter_crud
from app.schemas.encounter_schemas import LabOrderUpdate, RadiologyOrderUpdate, PrescriptionUpdate

router = APIRouter(tags=["Ancillary Services"])


# Laboratory Information System (LIS) Routes

@router.get("/lab", name="lab_dashboard")
def lab_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor", "Nurse", "Clinician"])),
    status_filter: Optional[str] = Query(None, description="Filter by order status"),
    search: Optional[str] = Query(None, description="Search by patient name, patient number, or phone number"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    priority: Optional[str] = Query(None, description="Filter by priority (stat, urgent, routine)"),
    test_type: Optional[str] = Query(None, description="Filter by test type/category")
):
    """
    Laboratory dashboard showing pending and completed lab orders.
    """
    from sqlalchemy import or_
    
    # Get counts for statistics cards — exclude AMENDED_VERSION archive records from all counts
    counts = {}
    base_query = db.query(LabOrder).filter(
        or_(LabOrder.result_status != 'AMENDED_VERSION', LabOrder.result_status.is_(None))
    )
    counts['pending'] = base_query.filter(LabOrder.status == OrderStatus.PENDING.value).count()
    counts['in_progress'] = base_query.filter(LabOrder.status == OrderStatus.IN_PROGRESS.value).count()
    counts['completed'] = base_query.filter(LabOrder.status == OrderStatus.COMPLETED.value).count()
    counts['total'] = base_query.count()
    
    # Priority-based counts
    priority_counts = {}
    priority_counts['stat'] = base_query.filter(LabOrder.priority == 'stat').count()
    priority_counts['urgent'] = base_query.filter(LabOrder.priority == 'urgent').count()
    priority_counts['routine'] = base_query.filter(LabOrder.priority == 'routine').count()
    
    # Today's statistics
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_counts = {}
    today_counts['total'] = base_query.filter(
        LabOrder.ordered_at >= today_start,
        LabOrder.ordered_at <= today_end
    ).count()
    today_counts['completed'] = base_query.filter(
        LabOrder.status == OrderStatus.COMPLETED.value,
        LabOrder.result_entered_at >= today_start,
        LabOrder.result_entered_at <= today_end
    ).count()
    today_counts['pending'] = counts['pending']
    
    # Query for lab orders — never show AMENDED_VERSION archive records in the list
    query = db.query(LabOrder).options(
        joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabOrder.ordered_by),
        joinedload(LabOrder.result_entered_by)
    ).filter(
        or_(LabOrder.result_status != 'AMENDED_VERSION', LabOrder.result_status.is_(None))
    )

    # Filter by status if provided
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(LabOrder.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show pending and in_progress orders
        query = query.filter(
            LabOrder.status.in_([OrderStatus.PENDING.value, OrderStatus.IN_PROGRESS.value])
        )
    
    # Filter by priority
    if priority:
        query = query.filter(LabOrder.priority == priority.lower())
    
    # Filter by test type (test_name contains)
    if test_type:
        query = query.filter(LabOrder.test_name.ilike(f"%{test_type}%"))
    
    # Filter by date range
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(LabOrder.ordered_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = datetime.combine(to_date, datetime.max.time())
            query = query.filter(LabOrder.ordered_at <= to_date)
        except ValueError:
            pass
    
    # Search by patient name, patient number, or phone number
    if search:
        search_term = f"%{search.strip()}%"
        # For walk-in orders, patient_id is directly on LabOrder
        # For encounter-based orders, patient is via Encounter
        query = query.outerjoin(Encounter).outerjoin(Patient, 
            or_(LabOrder.patient_id == Patient.id, Encounter.patient_id == Patient.id)
        ).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
            )
        )
    
    lab_orders = query.order_by(LabOrder.ordered_at.desc()).limit(100).all()
    
    # Check payment status for each lab order (for cash patients)
    # OPD: pay before lab results. IPD (on admission): pay at discharge — do not require payment before results.
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid
    from app.models.billing_models import Charge, ChargeType, Invoice
    from app.crud import ipd_crud
    lab_order_payment_status = {}
    
    for order in lab_orders:
        patient_id = None
        if order.encounter and order.encounter.patient:
            patient_id = order.encounter.patient.id
        elif order.patient_id:
            patient_id = order.patient_id
        
        if patient_id and is_cash_patient(db, patient_id):
            # Admitted (IPD) patients pay at discharge — allow lab results without prior payment
            current_admission = ipd_crud.get_current_admission(db, patient_id)
            if current_admission:
                lab_order_payment_status[order.id] = {
                    "payment_required": False,
                    "payment_paid": True,
                    "is_admitted": True
                }
                continue
            # OPD cash: require payment before lab results
            charge = db.query(Charge).filter(
                Charge.lab_order_id == order.id,
                Charge.charge_type == ChargeType.LAB_TEST,
                Charge.invoice.has(Invoice.is_active == True)
            ).first()
            
            if charge:
                invoice = charge.invoice
                payment_required, payment_paid, _, _ = check_payment_required_and_paid(
                    db, patient_id, ChargeType.LAB_TEST,
                    encounter_id=order.encounter_id if order.encounter else None,
                    lab_order_id=order.id
                )
                if payment_required and not payment_paid:
                    lab_order_payment_status[order.id] = {
                        "payment_required": True,
                        "payment_paid": False,
                        "invoice_id": invoice.id,
                        "balance": invoice.balance
                    }
                else:
                    lab_order_payment_status[order.id] = {
                        "payment_required": payment_required,
                        "payment_paid": True
                    }
    
    context = {
        "request": request,
        "title": "Laboratory (LIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "lab_orders": lab_orders,
        "lab_order_payment_status": lab_order_payment_status,
        "status_filter": status_filter,
        "search": search,
        "counts": counts,
        "priority_counts": priority_counts,
        "today_counts": today_counts,
        "date_from": date_from,
        "date_to": date_to,
        "priority_filter": priority,
        "test_type_filter": test_type
    }
    return templates.TemplateResponse("ancillary/lab_dashboard.html", context)


# Combined Lab Report Print Route - Print Multiple Tests in One Report
# NOTE: This route MUST be defined BEFORE /lab/orders/{order_id} to avoid being caught by the integer path parameter
@router.get("/lab/orders/print-combined", name="print_combined_lab_results")
def print_combined_lab_results(
    request: Request,
    order_ids: str = Query(..., description="Comma-separated list of lab order IDs"),
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor", "Nurse", "Clinician"]))
):
    """
    Print/Export multiple lab results for the same patient in a single combined report.
    
    This endpoint:
    - Validates all tests belong to the same patient
    - Validates all tests are completed/verified
    - Combines results into a single report with the existing template format
    - Groups tests by category if they have category information
    """
    from app.models.lab_models import LabSample
    from app.models.lab_template_models import LabTemplate, LabReferenceRange
    from app.services.lab_template_schema import normalize_template_schema
    from app.services.lab_template_resolution import resolve_template_for_order
    from app.services.reference_range_engine import get_field_reference_range
    from app.services.lab_result_validation import compute_flags
    
    # Parse order IDs
    try:
        order_id_list = [int(oid.strip()) for oid in order_ids.split(',') if oid.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order IDs format. Use comma-separated integers.")
    
    if not order_id_list:
        raise HTTPException(status_code=400, detail="No order IDs provided")
    
    if len(order_id_list) < 2:
        raise HTTPException(status_code=400, detail="At least 2 orders required for combined report")
    
    # Load all lab orders with relationships
    lab_orders = db.query(LabOrder).options(
        joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabOrder.ordered_by),
        joinedload(LabOrder.result_entered_by),
        joinedload(LabOrder.samples)
    ).filter(LabOrder.id.in_(order_id_list)).all()
    
    if not lab_orders:
        raise HTTPException(status_code=404, detail="No lab orders found")
    
    if len(lab_orders) != len(order_id_list):
        found_ids = {o.id for o in lab_orders}
        missing = set(order_id_list) - found_ids
        raise HTTPException(status_code=404, detail=f"Lab orders not found: {missing}")
    
    # Validate all orders belong to the same patient
    patient = None
    patient_id = None
    
    for order in lab_orders:
        if order.encounter and order.encounter.patient:
            order_patient_id = order.encounter.patient.id
        elif order.patient_id:
            order_patient_id = order.patient_id
        else:
            raise HTTPException(status_code=400, detail=f"Order {order.id} has no associated patient")
        
        if patient_id is None:
            patient_id = order_patient_id
        elif patient_id != order_patient_id:
            raise HTTPException(status_code=400, detail="All orders must belong to the same patient")
    
    # Get the patient object
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Validate all orders are completed/verified
    completed_statuses = [OrderStatus.COMPLETED.value, "VERIFIED", "RELEASED"]
    for order in lab_orders:
        if order.status != OrderStatus.COMPLETED.value and order.result_status not in completed_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Order {order.id} ({order.test_name}) is not completed. Status: {order.status}"
            )
    
    # Process each lab order to get results, schema, flags, and reference ranges
    processed_orders = []
    
    for lab_order in lab_orders:
        # Resolve template and get schema
        schema_json = None
        ref_ranges = {}
        flags_json = lab_order.flags_json if lab_order.flags_json else {}
        stored_ref_ranges = lab_order.reference_ranges_json if lab_order.reference_ranges_json else {}
        if stored_ref_ranges:
            ref_ranges = dict(stored_ref_ranges)
        
        try:
            resolved = resolve_template_for_order(db, lab_order, persist=False)
            
            if resolved and resolved.schema_json:
                schema_json = resolved.schema_json
                if isinstance(schema_json, str):
                    try:
                        schema_json = json.loads(schema_json)
                    except json.JSONDecodeError:
                        schema_json = None
                
                # Get reference ranges for each field
                if schema_json and patient:
                    patient_age_days = None
                    if patient.date_of_birth:
                        from datetime import date
                        today = date.today()
                        patient_age_days = (today - patient.date_of_birth).days
                    
                    for fcode, fdef in (schema_json.get('fields') or {}).items():
                        if fdef.get('type') in ('numeric', 'integer'):
                            try:
                                range_result = get_field_reference_range(
                                    db, fcode, 
                                    patient_age_days, patient.gender or 'ANY', None
                                )
                                if range_result:
                                    ref_ranges[fcode] = {
                                        'low': float(range_result.low) if range_result.low else None,
                                        'high': float(range_result.high) if range_result.high else None,
                                        'critical_low': float(range_result.critical_low) if range_result.critical_low else None,
                                        'critical_high': float(range_result.critical_high) if range_result.critical_high else None,
                                        'unit': fdef.get('unit', '') or range_result.unit or '',
                                        'text_range': range_result.text_range,
                                        'sex': range_result.sex,
                                        'age_range': f"{range_result.age_min_days // 365 if range_result.age_min_days else 0}-{range_result.age_max_days // 365 if range_result.age_max_days else 'Adult'}" if range_result.age_min_days or range_result.age_max_days else None
                                    }
                                    # Special override for Malaria Parasite density
                                    if fcode in ('trophozoite_count', 'TROPH_COUNT', 'parasite_density', 'PARASITE_DENSITY'):
                                        ref_ranges[fcode] = {
                                            'low': None, 'high': None, 'critical_low': None, 'critical_high': None,
                                            'unit': 'Parasites/µL',
                                            'text_range': 'NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL',
                                            'sex': 'ANY', 'age_range': None
                                        }
                            except Exception:
                                pass
                        elif fdef.get('reference_range'):
                            text_range = fdef.get('reference_range')
                            invalid_units = ['none', 'titer', 'n/a', 'not applicable', 'not seen', '']
                            field_unit = fdef.get('unit', '') or ''
                            text_range_unit = text_range.get('units', '') if isinstance(text_range, dict) else ''
                            display_unit = field_unit if field_unit and field_unit.lower() not in invalid_units else (text_range_unit if text_range_unit and text_range_unit.lower() not in invalid_units else '')
                            display_unit = '' if display_unit.lower() in invalid_units else display_unit
                            display_text_range = text_range
                            if isinstance(text_range, dict):
                                display_text_range = text_range.get('text_range') or text_range.get('normal_range') or text_range
                                if isinstance(display_text_range, dict):
                                    display_text_range = text_range
                            if isinstance(display_text_range, str) and display_text_range.lower() in ['not seen', 'not applicable', 'n/a', 'none', '']:
                                display_text_range = None
                            ref_ranges[fcode] = {
                                'low': None, 'high': None, 'critical_low': None, 'critical_high': None,
                                'unit': display_unit, 'text_range': display_text_range,
                                'sex': fdef.get('sex', 'ANY'), 'age_range': fdef.get('age_range', None)
                            }
        except Exception as e:
            print(f"Error resolving template for order {lab_order.id}: {e}")
        
        # Compute flags based on reference ranges
        if ref_ranges and lab_order.result_json and schema_json:
            try:
                patient_context = {
                    "gender": patient.gender,
                    "date_of_birth": patient.date_of_birth
                }
                computed_flags = compute_flags(db, schema_json, lab_order.result_json, patient_context)
                if computed_flags:
                    flags_json = {}
                    for flag_info in computed_flags:
                        flags_json[flag_info.field_code] = {
                            "flag": flag_info.flag,
                            "value": flag_info.value,
                            "low": flag_info.low,
                            "high": flag_info.high,
                            "critical_low": flag_info.critical_low,
                            "critical_high": flag_info.critical_high
                        }
            except Exception as e:
                print(f"Error computing flags for order {lab_order.id}: {e}")
        
        # Normalize schema
        normalized_schema = normalize_template_schema(schema_json)
        
        # Calculate turnaround time
        turnaround_time = None
        if lab_order.ordered_at and lab_order.result_entered_at:
            delta = lab_order.result_entered_at - lab_order.ordered_at
            hours = delta.total_seconds() / 3600
            if hours < 24:
                turnaround_time = f"{int(hours)} hour(s)"
            else:
                days = hours / 24
                turnaround_time = f"{days:.1f} day(s)"
        
        processed_orders.append({
            "lab_order": lab_order,
            "result_json": lab_order.result_json or {},
            "schema_json": normalized_schema,
            "flags_json": flags_json,
            "ref_ranges": ref_ranges,
            "turnaround_time": turnaround_time,
            "result_entered_by": lab_order.result_entered_by,
            "samples": lab_order.samples,
        })
    
    # Get hospital settings
    from app.crud import hospital_settings_crud
    try:
        hospital_settings = hospital_settings_crud.get_hospital_settings(db)
        if not hospital_settings:
            import types
            hospital_settings = types.SimpleNamespace(
                hospital_name="DEI GRATIA MEDICAL SERVICES",
                hospital_address="North Dungu, Opposite Quantum Filling Station, Wayamba Junction, BLK A121, Tamale - Bolgatanga Road",
                hospital_phone="0546731001 / 0207642170",
                hospital_email="deigratiamsl@gmail.com",
                logo_url="/uploads/logos/hospital_logo.png",
                logo_path="uploads/logos/hospital_logo.png",
                lab_contact_email=None,
                lab_contact_phone=None,
                accreditation=None,
                accreditation_number=None
            )
    except Exception:
        import types
        hospital_settings = types.SimpleNamespace(
            hospital_name="DEI GRATIA MEDICAL SERVICES",
            hospital_address="North Dungu, Opposite Quantum Filling Station, Wayamba Junction, BLK A121, Tamale - Bolgatanga Road",
            hospital_phone="0546731001 / 0207642170",
            hospital_email="deigratiamsl@gmail.com",
            logo_url="/uploads/logos/hospital_logo.png",
            logo_path="uploads/logos/hospital_logo.png",
            lab_contact_email=None,
            lab_contact_phone=None,
            accreditation=None,
            accreditation_number=None
        )
    
    # Get list of test names for the combined report
    test_names = [order["lab_order"].test_name for order in processed_orders]
    combined_test_names = ", ".join(test_names)
    
    return templates.TemplateResponse(
        "lab/print_combined_lab_result.html",
        {
            "request": request,
            "patient": patient,
            "lab_orders": processed_orders,
            "test_names": combined_test_names,
            "hospital_settings": hospital_settings,
            "now": datetime.now(),
        }
    )


@router.get("/lab/orders/{order_id}", name="view_lab_order")
def view_lab_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor", "Nurse", "Clinician"]))
):
    """
    View a specific lab order and enter results.
    """
    from app.models.lab_models import LabSample
    
    lab_order = db.query(LabOrder).options(
        joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabOrder.ordered_by),
        joinedload(LabOrder.result_entered_by),
        joinedload(LabOrder.samples)
    ).filter(LabOrder.id == order_id).first()
    
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Check payment status for cash patients.
    # OPD: pay before lab results. IPD (on admission): pay at discharge — allow result entry without prior payment.
    from app.utils.payment_verification import is_cash_patient, has_visit_invoice_been_paid
    from app.models.billing_models import Invoice
    from app.crud import ipd_crud
    
    patient = lab_order.encounter.patient if lab_order.encounter else (db.query(Patient).filter(Patient.id == lab_order.patient_id).first() if lab_order.patient_id else None)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found for this lab order")
    
    # If there's already a result (from a previous entry or amendment), don't require payment for viewing/amending
    # Payment was already made when the original result was entered
    has_existing_result = bool(lab_order.result or lab_order.result_json)
    
    payment_required = False
    payment_paid = True
    payment_notice = None
    unpaid_invoice = None
    paid_invoice = None
    is_admitted = False
    
    # Skip payment check if result already exists (amendment case)
    if has_existing_result:
        payment_notice = "Note: This order has an existing result. Amendments do not require additional payment."
    elif is_cash_patient(db, patient.id):
        # Admitted (IPD) patients pay at discharge — allow lab results without prior payment
        current_admission = ipd_crud.get_current_admission(db, patient.id)
        if current_admission:
            is_admitted = True
            payment_required = False
            payment_paid = True
            payment_notice = "Patient is on admission (IPD). Payment will be at discharge. You can enter results."
        else:
            # Check for walk-in patient or OPD patient
            if lab_order.is_walk_in:
                # For walk-in patients, check if the lab order's invoice is paid
                from app.models.billing_models import Charge
                charge = db.query(Charge).filter(
                    Charge.lab_order_id == lab_order.id,
                    Charge.is_active == True
                ).first()
                if charge and charge.invoice_id:
                    invoice = db.query(Invoice).filter(
                        Invoice.id == charge.invoice_id,
                        Invoice.is_active == True
                    ).first()
                    if invoice and invoice.balance <= 0:
                        payment_paid = True
                        paid_invoice = invoice
                        payment_notice = "Payment Status: Walk-in lab order has been paid. You can enter results."
                    else:
                        payment_paid = False
                        payment_required = True
                        if invoice:
                            unpaid_invoice = invoice
                            payment_notice = f"Payment Required: Walk-in lab order not paid. Outstanding balance: GHS {invoice.balance:.2f}"
                        else:
                            payment_notice = "Payment Required: No invoice found for this walk-in lab order."
                else:
                    # No charge yet - create one
                    from app.services import create_charge_for_lab_order
                    try:
                        create_charge_for_lab_order(db, lab_order, current_user.id, check_payment_required=False)
                    except Exception:
                        pass
                    payment_notice = "Payment Required: Please pay for this walk-in lab order first."
                    payment_required = True
            else:
                # OPD: visit invoice (consultation + lab) must be paid before result entry
                from app.services import create_charge_for_lab_order
                try:
                    create_charge_for_lab_order(db, lab_order, current_user.id, check_payment_required=False)
                except Exception:
                    pass
                payment_paid = has_visit_invoice_been_paid(db, encounter_id=lab_order.encounter_id) if lab_order.encounter_id else False
                payment_required = not payment_paid
                invoice = db.query(Invoice).filter(
                    Invoice.encounter_id == lab_order.encounter_id,
                    Invoice.is_active == True
                ).first() if lab_order.encounter_id else None
                if invoice:
                    if payment_paid:
                        paid_invoice = invoice
                        payment_notice = "Payment Status: Visit (consultation + lab) has been paid. You can enter results."
                    else:
                        unpaid_invoice = invoice
                        payment_notice = f"Payment Required: Patient must pay visit (consultation + lab) before lab result. Balance: GHS {invoice.balance:.2f}"
    
    # Get samples for this order
    samples = db.query(LabSample).filter(
        LabSample.lab_order_id == order_id,
        LabSample.is_active == True
    ).all()
    
    # Resolve template schema for result entry
    schema_json = None
    template_version_used = None
    ref_ranges = {}
    option_sets = {}
    has_critical_fields = False
    try:
        from app.services.lab_template_resolution import resolve_template_for_order, TemplateResolutionError
        try:
            resolved = resolve_template_for_order(db, lab_order, persist=True)
            schema_json = resolved.schema_json
            template_version_used = resolved.template_version
            db.commit()  # Persist template_id and version to lab_order
            
            # Load reference ranges for numeric fields
            if schema_json and patient:
                from app.services.reference_range_engine import get_field_reference_range
                patient_age_days = None
                if patient.date_of_birth:
                    from datetime import date
                    today = date.today()
                    patient_age_days = (today - patient.date_of_birth).days
                
                for fcode, fdef in (schema_json.get("fields") or {}).items():
                    # Check for critical fields
                    if fdef.get("critical"):
                        has_critical_fields = True
                    
                    # Get reference ranges for numeric fields
                    if fdef.get("type") in ("numeric", "integer"):
                        range_result = get_field_reference_range(
                            db, fcode, 
                            patient_age_days=patient_age_days,
                            patient_sex=patient.gender
                        )
                        if range_result:
                            ref_ranges[fcode] = {
                                "low": float(range_result.low) if range_result.low is not None else None,
                                "high": float(range_result.high) if range_result.high is not None else None,
                                "critical_low": float(range_result.critical_low) if range_result.critical_low is not None else None,
                                "critical_high": float(range_result.critical_high) if range_result.critical_high is not None else None,
                                "unit": fdef.get("unit", "") or range_result.unit or '',
                                "text_range": range_result.text_range
                            }
                            # Special override for Trophozoites Count - ALWAYS use the malaria density interpretation scale
                            # This ensures the correct reference range is always shown regardless of stored values
                            if fcode in ('trophozoite_count', 'TROPH_COUNT', 'parasite_density', 'PARASITE_DENSITY'):
                                # Always set the malaria parasite density interpretation scale
                                ref_ranges[fcode] = {
                                    'low': None,
                                    'high': None,
                                    'critical_low': None,
                                    'critical_high': None,
                                    'unit': 'Parasites/µL',
                                    'text_range': 'NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL'
                                }
                                print(f"DEBUG: view_lab_order - Overrode trophozoite_count reference range to malaria density scale")
                            # If numeric values are None, try to extract from template's reference_range
                            if ref_ranges[fcode]['low'] is None and ref_ranges[fcode]['high'] is None:
                                template_ref = fdef.get('reference_range', {})
                                if template_ref:
                                    # Check age applicability before using template values
                                    NEONATE_MAX_DAYS = 28
                                    CHILD_MAX_DAYS = 6570
                                    ADULT_MIN_DAYS = 6570
                                    ELDERLY_MIN_DAYS = 21900
                                    
                                    is_age_appropriate = False
                                    if template_ref.get('all_ages', False):
                                        is_age_appropriate = True
                                    elif patient_age_days is not None:
                                        if patient_age_days <= NEONATE_MAX_DAYS and template_ref.get('applies_to_neonates', False):
                                            is_age_appropriate = True
                                        elif patient_age_days < ADULT_MIN_DAYS and template_ref.get('applies_to_children', False):
                                            is_age_appropriate = True
                                        elif patient_age_days >= ADULT_MIN_DAYS and template_ref.get('applies_to_adults', False):
                                            is_age_appropriate = True
                                        elif patient_age_days >= ELDERLY_MIN_DAYS and template_ref.get('applies_to_elderly', False):
                                            is_age_appropriate = True
                                    else:
                                        is_age_appropriate = template_ref.get('all_ages', True)
                                    
                                    if is_age_appropriate:
                                        normal_val = template_ref.get('normal_value')
                                        if normal_val is not None:
                                            try:
                                                ref_ranges[fcode]['low'] = float(normal_val)
                                                ref_ranges[fcode]['high'] = ref_ranges[fcode]['low']
                                            except (ValueError, TypeError):
                                                pass
                                        if not ref_ranges[fcode].get('text_range'):
                                            template_text_range = template_ref.get('text_range')
                                            if template_text_range:
                                                ref_ranges[fcode]['text_range'] = template_text_range
                                        if not ref_ranges[fcode].get('unit'):
                                            ref_ranges[fcode]['unit'] = template_ref.get('units', '')
                    
                    # Get option sets for choice fields
                    if fdef.get("optionSet"):
                        from app.models.lab_template_models import LabOptionSet
                        os_obj = db.query(LabOptionSet).filter(LabOptionSet.name == fdef["optionSet"]).first()
                        if os_obj and os_obj.options_json:
                            option_sets[fdef["optionSet"]] = os_obj.options_json
        except TemplateResolutionError as e:
            # No template configured - will show plain text field
            print(f"Template resolution warning for order {order_id}: {e}")
    except Exception as e:
        print(f"Error resolving template for order {order_id}: {e}")
    
    # Initialize flags_json with stored value, will be recomputed if ref_ranges are available
    flags_json = lab_order.flags_json if lab_order.flags_json else {}
    
    # Compute flags based on newly computed reference ranges
    # This ensures flags are accurate even if stored flags are outdated
    if ref_ranges and lab_order.result_json:
        try:
            from app.services.lab_result_validation import compute_flags
            
            # Build patient context for flag computation
            patient_context = {}
            if patient:
                patient_context["gender"] = patient.gender
                patient_context["date_of_birth"] = patient.date_of_birth
            
            # Compute flags using the schema and result
            if schema_json:
                computed_flags = compute_flags(db, schema_json, lab_order.result_json, patient_context)
                
                # Convert flags to the expected format
                if computed_flags:
                    flags_json = {}
                    for flag_info in computed_flags:
                        flags_json[flag_info.field_code] = {
                            "flag": flag_info.flag,
                            "value": flag_info.value,
                            "low": flag_info.low,
                            "high": flag_info.high,
                            "critical_low": flag_info.critical_low,
                            "critical_high": flag_info.critical_high
                        }
                    print(f"DEBUG: Computed {len(computed_flags)} flags from ref_ranges")
        except Exception as flag_err:
            print(f"Error computing flags: {flag_err}")
    
    context = {
        "request": request,
        "title": f"Lab Order #{order_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "lab_order": lab_order,
        "patient": patient,
        "samples": samples,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "paid_invoice": paid_invoice,
        "is_admitted": is_admitted,
        "schema_json": schema_json,
        "_schema": schema_json,  # Alias for template compatibility
        "ref_ranges": ref_ranges,
        "flags_json": flags_json,
        "option_sets": option_sets,
        "has_critical_fields": has_critical_fields,
        "result_json": lab_order.result_json or {},
    }
    return templates.TemplateResponse("ancillary/lab_order_detail.html", context)


@router.post("/lab/orders/{order_id}/enter-result", name="enter_lab_result", status_code=status.HTTP_302_FOUND)
async def enter_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
    result: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None)
):
    """
    Enter lab test results.
    OPD cash patients: must pay before lab results. IPD (on admission): pay at discharge — allow result entry.
    """
    # Validate that result is provided
    if not result:
        # Check if this is a template-based submission by looking for result_* fields in request
        # This handles the case where JavaScript collects fields but result field is missing
        try:
            form_data = await request.form()
            # Look for any result_* fields which would indicate template-based entry
            template_fields = [key for key in form_data.keys() if key.startswith('result_')]
            if template_fields:
                # Build result from template fields
                import json
                result_data = {}
                for key in template_fields:
                    field_code = key.replace('result_', '')
                    value = form_data.get(key)
                    if value:
                        try:
                            # Try to parse as number
                            result_data[field_code] = float(value) if '.' in value else int(value)
                        except ValueError:
                            result_data[field_code] = value
                result = json.dumps(result_data)
            else:
                raise HTTPException(status_code=400, detail="Result is required. Please enter test results.")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Result is required. Please enter test results. Error: {str(e)}")
    from app.utils.payment_verification import (
        is_cash_patient,
        has_visit_invoice_been_paid
    )
    from app.models.billing_models import Invoice
    from app.crud import ipd_crud
    
    lab_order = db.query(LabOrder).options(
        joinedload(LabOrder.encounter)
    ).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    encounter = lab_order.encounter
    patient_id = encounter.patient_id if encounter else lab_order.patient_id
    if not patient_id:
        raise HTTPException(status_code=400, detail="Patient not found for this lab order")
    
    # OPD cash: pay before lab results. IPD (on admission): pay at discharge — allow result entry without prior payment.
    if is_cash_patient(db, patient_id):
        current_admission = ipd_crud.get_current_admission(db, patient_id)
        if not current_admission:
            # OPD: block result entry until visit invoice paid
            if encounter and not has_visit_invoice_been_paid(db, encounter_id=encounter.id):
                pay_url = request.url_for("pay_consultation", patient_id=patient_id)
                return RedirectResponse(
                    url=f"{pay_url}?encounter_id={encounter.id}&return_to=pay_visit&from_lab={order_id}",
                    status_code=status.HTTP_302_FOUND
                )
    
    # Update lab order with result
    update_data = {
        "result": result,
        "result_entered_by_id": current_user.id,
        "result_entered_at": datetime.now(),
        "status": OrderStatus.COMPLETED.value,
        "completed_at": datetime.now()
    }
    
    # If result is JSON (from structured template), also store in result_json and compute flags
    import json
    try:
        result_json_data = json.loads(result)
        if isinstance(result_json_data, dict):
            update_data["result_json"] = result_json_data
            
            # Compute flags for numeric results based on reference ranges
            try:
                from app.services.result_interpretation import interpret_results_batch
                from app.services.reference_range_engine import get_field_reference_range
                from app.models.patient_models import Patient
                from datetime import date
                
                # Get patient for reference range calculation
                patient = None
                if encounter and encounter.patient:
                    patient = encounter.patient
                elif lab_order.patient_id:
                    patient = db.query(Patient).filter(Patient.id == lab_order.patient_id).first()
                
                if patient and lab_order.lab_test_id:
                    # Get the template schema if available
                    from app.services.lab_template_resolution import resolve_template_for_order
                    resolved = resolve_template_for_order(db, lab_order, persist=False)
                    
                    if resolved and resolved.schema_json:
                        # Ensure schema_json is a dict
                        schema = resolved.schema_json
                        if isinstance(schema, str):
                            import json
                            try:
                                schema = json.loads(schema)
                            except json.JSONDecodeError:
                                schema = None
                        
                        if schema:
                            # Calculate patient age
                            patient_age_days = None
                            if patient.date_of_birth:
                                today = date.today()
                                patient_age_days = (today - patient.date_of_birth).days
                            
                            # Interpret results and get flags
                            interpretation_result = interpret_results_batch(
                                db=db,
                                results=result_json_data,
                                patient_age_days=patient_age_days,
                                patient_sex=patient.gender,
                                template_fields=schema.get('fields', {})
                            )
                            
                            # Format flags as {field_code: {flag: 'HIGH'}} for template compatibility
                            if interpretation_result and 'flags' in interpretation_result:
                                flags_formatted = {}
                                for field_code, flag in interpretation_result['flags'].items():
                                    flags_formatted[field_code] = {'flag': flag}
                                update_data["flags_json"] = flags_formatted
                            
                            # Store reference ranges used for interpretation
                            if interpretation_result and 'interpreted_results' in interpretation_result:
                                ref_ranges = {}
                                for field_code, interp in interpretation_result['interpreted_results'].items():
                                    if field_code in result_json_data:
                                        ref_ranges[field_code] = {
                                            'low': interp.get('reference_low'),
                                            'high': interp.get('reference_high'),
                                            'critical_low': interp.get('critical_low'),
                                            'critical_high': interp.get('critical_high'),
                                            'unit': interp.get('unit'),
                                            'text_range': interp.get('interpretation')
                                        }
                                if ref_ranges:
                                    update_data["reference_ranges_json"] = ref_ranges
            except Exception as flag_error:
                print(f"Error computing flags: {flag_error}")
                # Continue without flags if there's an error
    except (json.JSONDecodeError, TypeError):
        # Not JSON, keep result as free text
        pass
    
    # Send SMS notification to patient when result is ready (only if valid phone)
    try:
        from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
        patient = encounter.patient if encounter else db.query(Patient).filter(Patient.id == patient_id).first()
        if patient and patient.phone_number and is_valid_phone(patient.phone_number):
            message_template = "Hello {$name}. Your lab test result for {$test_name} is ready. Please visit the hospital or contact your doctor. Thank you!"
            destinations = [{
                "number": patient.phone_number,
                "values": [
                    f"{patient.first_name} {patient.last_name}",
                    lab_order.test_name
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
    except Exception as sms_error:
        print(f"Warning: Unable to send lab result SMS: {sms_error}")
    
    # Validate result before saving
    validation_status = None
    try:
        from app.services import validate_lab_result
        validation = validate_lab_result(db, lab_order, result)
        validation_status = validation.status
        
        # Add validation warnings to result if any
        if validation.warnings:
            result = f"{result}\n\n[Validation Notes: {', '.join(validation.warnings)}]"
    except Exception as e:
        # Log validation error but continue
        print(f"Error validating lab result {order_id}: {e}")
    
    # Handle file uploads if provided
    if files:
        # patient_id already set above (encounter or lab_order.patient_id)
        
        # Create storage directory
        storage_base = "static/files/lab_results"
        storage_path = os.path.join(storage_base, str(patient_id), str(order_id))
        os.makedirs(storage_path, exist_ok=True)
        
        uploaded_files = []
        for file in files:
            if file.filename:
                # Generate unique filename
                file_ext = os.path.splitext(file.filename)[1] or ""
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(storage_path, unique_filename)
                
                # Save file
                with open(file_path, "wb") as f:
                    content = file.file.read()
                    f.write(content)
                
                uploaded_files.append({
                    "original_name": file.filename,
                    "saved_path": file_path,
                    "file_size": len(content),
                    "file_type": file.content_type or "application/octet-stream"
                })
        
        # Store file info in result text (or could create separate model)
        if uploaded_files:
            file_info = "\n\n[Attached Files: " + ", ".join([f.filename for f in files]) + "]"
            result = result + file_info
            # Update result in update_data
            update_data["result"] = result
    
    lab_order_update = LabOrderUpdate(**update_data)
    updated_lab_order = encounter_crud.update_lab_order(db, order_id, lab_order_update)
    
    # Automatically create charge when lab order is completed
    if updated_lab_order and updated_lab_order.status == OrderStatus.COMPLETED.value:
        try:
            from app.services import create_charge_for_lab_order
            create_charge_for_lab_order(db, updated_lab_order, current_user.id)
        except Exception as e:
            # Log error but don't fail the request
            # In production, use proper logging
            print(f"Error creating charge for lab order {order_id}: {e}")
    
    # Redirect with validation status
    redirect_url = f"/api/v1/ancillary/lab/orders/{order_id}?status=result_entered"
    if validation_status and validation_status in ["critical", "abnormal"]:
        redirect_url += f"&validation={validation_status}"
    
    return RedirectResponse(
        url=redirect_url,
        status_code=status.HTTP_302_FOUND
    )


@router.post("/lab/orders/{order_id}/amend-result", name="amend_lab_result", status_code=status.HTTP_302_FOUND)
async def amend_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"])),
):
    """
    Amend a lab result — simple in-place edit, no duplicate records created.
    Accepts result_* fields (template-based) or a single 'result' field (free-text),
    plus a required 'amend_reason' field.
    """
    import json
    from datetime import date as _date

    form_data = await request.form()
    amend_reason = (form_data.get("amend_reason") or "").strip()

    if not amend_reason:
        raise HTTPException(status_code=400, detail="Amendment reason is required.")

    lab_order = db.query(LabOrder).options(
        joinedload(LabOrder.encounter)
    ).filter(LabOrder.id == order_id).first()

    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")

    if not lab_order.result and not lab_order.result_json:
        raise HTTPException(status_code=400, detail="Cannot amend: no existing result on this order.")

    # ── Collect new result values ──────────────────────────────────────────────
    template_keys = [k for k in form_data.keys() if k.startswith("result_")]
    result_json_data = None
    result_text = None

    if template_keys:
        # Template-based: build result_json from result_* form fields
        result_json_data = {}
        for key in template_keys:
            field_code = key[len("result_"):]
            raw = form_data.get(key)
            if raw is not None and raw != "":
                try:
                    result_json_data[field_code] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    result_json_data[field_code] = raw
        result_text = json.dumps(result_json_data)
    else:
        result_text = (form_data.get("result") or "").strip() or None

    if not result_text and not result_json_data:
        raise HTTPException(status_code=400, detail="Result is required.")

    # ── Build update payload ───────────────────────────────────────────────────
    update_data = {
        "result": result_text,
        "result_entered_by_id": current_user.id,
        "result_entered_at": datetime.now(),
        "result_status": "AMENDED",
        "amend_reason": amend_reason,
    }

    if result_json_data:
        update_data["result_json"] = result_json_data

        # Recompute flags with corrected values
        try:
            from app.services.result_interpretation import interpret_results_batch
            from app.models.patient_models import Patient

            patient = None
            if lab_order.encounter and lab_order.encounter.patient:
                patient = lab_order.encounter.patient
            elif lab_order.patient_id:
                patient = db.query(Patient).filter(Patient.id == lab_order.patient_id).first()

            if patient and lab_order.lab_test_id:
                from app.services.lab_template_resolution import resolve_template_for_order
                resolved = resolve_template_for_order(db, lab_order, persist=False)
                if resolved and resolved.schema_json:
                    schema = resolved.schema_json
                    if isinstance(schema, str):
                        try:
                            schema = json.loads(schema)
                        except json.JSONDecodeError:
                            schema = None
                    if schema:
                        patient_age_days = None
                        if patient.date_of_birth:
                            patient_age_days = (_date.today() - patient.date_of_birth).days

                        interp = interpret_results_batch(
                            db=db,
                            results=result_json_data,
                            patient_age_days=patient_age_days,
                            patient_sex=patient.gender,
                            template_fields=schema.get("fields", {})
                        )
                        if interp and "flags" in interp:
                            update_data["flags_json"] = {
                                fc: {"flag": f} for fc, f in interp["flags"].items()
                            }
                        if interp and "interpreted_results" in interp:
                            rr = {}
                            for fc, v in interp["interpreted_results"].items():
                                if fc in result_json_data:
                                    rr[fc] = {
                                        "low": v.get("reference_low"),
                                        "high": v.get("reference_high"),
                                        "critical_low": v.get("critical_low"),
                                        "critical_high": v.get("critical_high"),
                                        "unit": v.get("unit"),
                                        "text_range": v.get("interpretation"),
                                    }
                            if rr:
                                update_data["reference_ranges_json"] = rr
        except Exception as e:
            print(f"Error computing flags during amendment of order {order_id}: {e}")

    # ── Apply in-place ─────────────────────────────────────────────────────────
    for field, value in update_data.items():
        setattr(lab_order, field, value)
    lab_order.updated_at = datetime.now()
    db.commit()

    return RedirectResponse(
        url=f"/api/v1/ancillary/lab/orders/{order_id}?status=result_amended",
        status_code=status.HTTP_302_FOUND
    )


# Radiology Information System (RIS) Routes
@router.get("/radiology", name="radiology_dashboard")
def radiology_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"])),  # Radiology accessible to Admin, Clinicians, and Radiology Staff
    status_filter: Optional[str] = Query(None, description="Filter by order status"),
    search: Optional[str] = Query(None, description="Search by patient name, patient number, or phone number")
):
    """
    Radiology dashboard showing pending and completed radiology orders.
    """
    from sqlalchemy import or_
    
    # Query for radiology orders
    query = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient),
        joinedload(RadiologyOrder.patient),  # For walk-in patients without encounter
        joinedload(RadiologyOrder.ordered_by),
        joinedload(RadiologyOrder.report_entered_by)
    )
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(RadiologyOrder.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show pending and in_progress orders
        query = query.filter(
            RadiologyOrder.status.in_([OrderStatus.PENDING.value, OrderStatus.IN_PROGRESS.value])
        )
    
    # Search by patient name, patient number, or phone number
    if search:
        search_term = f"%{search.strip()}%"
        # For walk-in orders, patient_id is directly on RadiologyOrder
        # For encounter-based orders, patient is via Encounter
        query = query.outerjoin(Encounter).outerjoin(Patient, 
            or_(RadiologyOrder.patient_id == Patient.id, Encounter.patient_id == Patient.id)
        ).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
            )
        )
    
    radiology_orders = query.order_by(RadiologyOrder.ordered_at.desc()).limit(100).all()
    
    # Check payment status for each radiology order (for cash patients)
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid
    from app.models.billing_models import Charge, ChargeType, Invoice
    radiology_order_payment_status = {}
    
    for order in radiology_orders:
        patient_id = None
        if order.encounter and order.encounter.patient:
            patient_id = order.encounter.patient.id
        elif order.patient_id:
            patient_id = order.patient_id
        
        if patient_id and is_cash_patient(db, patient_id):
            # Check if there's a charge for this radiology order
            charge = db.query(Charge).filter(
                Charge.radiology_order_id == order.id,
                Charge.charge_type == ChargeType.RADIOLOGY,
                Charge.invoice.has(Invoice.is_active == True)
            ).first()
            
            if charge:
                invoice = charge.invoice
                payment_required, payment_paid, _, _ = check_payment_required_and_paid(
                    db, patient_id, ChargeType.RADIOLOGY,
                    encounter_id=order.encounter_id if order.encounter else None,
                    radiology_order_id=order.id
                )
                if payment_required and not payment_paid:
                    radiology_order_payment_status[order.id] = {
                        "payment_required": True,
                        "payment_paid": False,
                        "invoice_id": invoice.id,
                        "balance": invoice.balance
                    }
                else:
                    radiology_order_payment_status[order.id] = {
                        "payment_required": payment_required,
                        "payment_paid": True
                    }
    
    context = {
        "request": request,
        "title": "Radiology (RIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_orders": radiology_orders,
        "radiology_order_payment_status": radiology_order_payment_status,
        "status_filter": status_filter,
        "search": search
    }
    return templates.TemplateResponse("ancillary/radiology_dashboard.html", context)


@router.get("/radiology/orders/{order_id}", name="view_radiology_order")
def view_radiology_order(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"]))
):
    """
    View a specific radiology order and enter report.
    """
    radiology_order = db.query(RadiologyOrder).options(
        joinedload(RadiologyOrder.encounter).joinedload(Encounter.patient),
        joinedload(RadiologyOrder.ordered_by),
        joinedload(RadiologyOrder.report_entered_by),
        joinedload(RadiologyOrder.images)
    ).filter(RadiologyOrder.id == order_id).first()
    
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    # Check payment status for cash patients
    from app.utils.payment_verification import (
        is_cash_patient,
        check_payment_required_and_paid,
        requires_payment_before_service
    )
    from app.models.billing_models import ChargeType
    
    patient = radiology_order.encounter.patient
    payment_required = False
    payment_paid = True
    payment_notice = None
    unpaid_invoice = None
    paid_invoice = None
    
    if is_cash_patient(db, patient.id):
        # First, ensure charge exists for this radiology order (if not already created)
        # This allows us to always check payment status
        from app.services import create_charge_for_radiology_order
        try:
            create_charge_for_radiology_order(db, radiology_order, current_user.id, check_payment_required=False)
        except Exception as e:
            # Charge might already exist, continue
            pass
        
        # Check payment requirement and status
        payment_required = requires_payment_before_service(
            db, patient.id, ChargeType.RADIOLOGY
        )
        
        if payment_required:
            payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
                db, patient.id, ChargeType.RADIOLOGY,
                encounter_id=radiology_order.encounter_id,
                radiology_order_id=order_id
            )
            
            if invoice:
                if payment_paid:
                    paid_invoice = invoice
                    payment_notice = f"Payment Status: Patient has paid for this radiology order. Invoice #{invoice.invoice_number} - Amount: GHS {invoice.total_amount:.2f}"
                else:
                    unpaid_invoice = invoice
                    payment_notice = f"Payment Required: Patient has not paid for this radiology order. Outstanding balance: GHS {invoice.balance:.2f}"
            else:
                # Charge might not exist yet or still being created
                payment_notice = "Payment Status: Checking payment status..."
    
    context = {
        "request": request,
        "title": f"Radiology Order #{order_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "radiology_order": radiology_order,
        "patient": radiology_order.encounter.patient,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "paid_invoice": paid_invoice
    }
    return templates.TemplateResponse("ancillary/radiology_order_detail.html", context)


@router.post("/radiology/orders/{order_id}/enter-report", name="enter_radiology_report", status_code=status.HTTP_302_FOUND)
def enter_radiology_report(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Doctor", "Clinician", "Radiology Staff"])),
    report: str = Form(...)
):
    """
    Enter radiology report.
    For cash patients: Checks if payment has been made before allowing report entry.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    
    radiology_order = db.query(RadiologyOrder).filter(RadiologyOrder.id == order_id).first()
    if not radiology_order:
        raise HTTPException(status_code=404, detail="Radiology order not found")
    
    # Get patient from encounter
    encounter = radiology_order.encounter
    patient_id = encounter.patient_id
    
    # Check payment requirement for cash patients (radiology fee)
    # Payment must be made before saving reports for cash patients
    if is_cash_patient(db, patient_id):
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.RADIOLOGY,
            encounter_id=encounter.id, radiology_order_id=order_id
        )
        
        if payment_required and not payment_paid:
            # Block saving - redirect back with payment required error
            invoice_id = invoice.id if invoice else None
            invoice_balance = invoice.balance if invoice else None
            return RedirectResponse(
                url=f"/radiology/orders/{order_id}?error=payment_required&invoice_id={invoice_id}&balance={invoice_balance}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Update radiology order with report
    update_data = {
        "report": report,
        "report_entered_by_id": current_user.id,
        "report_entered_at": datetime.now(),
        "status": OrderStatus.COMPLETED.value,
        "completed_at": datetime.now()
    }
    
    # Validate report before saving
    try:
        from app.services import validate_radiology_report
        validation = validate_radiology_report(db, radiology_order, report)
        if not validation.is_valid:
            # If validation fails, redirect back with error
            return RedirectResponse(
                url=f"/radiology/orders/{order_id}?error={validation.message}",
                status_code=status.HTTP_302_FOUND
            )
    except Exception as e:
        # Log validation error but continue
        print(f"Error validating radiology report {order_id}: {e}")
    
    radiology_order_update = RadiologyOrderUpdate(**update_data)
    updated_radiology_order = encounter_crud.update_radiology_order(db, order_id, radiology_order_update)
    
    # Send SMS notification to patient when radiology result is ready (only if valid phone)
    try:
        from app.services.sms_onlinegh_service import send_personalized_sms_notification, is_valid_phone
        patient = encounter.patient
        if patient and patient.phone_number and is_valid_phone(patient.phone_number):
            message_template = "Hello {$name}. Your radiology result for {$study_type} is ready. Please visit the hospital or contact your doctor. Thank you!"
            destinations = [{
                "number": patient.phone_number,
                "values": [
                    f"{patient.first_name} {patient.last_name}",
                    radiology_order.study_type
                ]
            }]
            send_personalized_sms_notification(message_template, destinations)
    except Exception as sms_error:
        print(f"Warning: Unable to send radiology result SMS: {sms_error}")
    
    # Automatically create charge when radiology order is completed
    if updated_radiology_order and updated_radiology_order.status == OrderStatus.COMPLETED.value:
        try:
            from app.services import create_charge_for_radiology_order
            create_charge_for_radiology_order(db, updated_radiology_order, current_user.id)
        except Exception as e:
            # Log error but don't fail the request
            # In production, use proper logging
            print(f"Error creating charge for radiology order {order_id}: {e}")
    
    # Redirect with success status
    return RedirectResponse(
        url=f"/radiology/orders/{order_id}?status=report_entered",
        status_code=status.HTTP_302_FOUND
    )


# Pharmacy Information System (PhIS) Routes
@router.get("/pharmacy", name="pharmacy_dashboard")
def pharmacy_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin", "Doctor", "Nurse", "Clinician"])),
    status_filter: Optional[str] = Query(None, description="Filter by prescription status"),
    search: Optional[str] = Query(None, description="Search by patient name, patient number, or phone number")
):
    """
    Pharmacy dashboard showing pending and completed prescriptions.
    """
    from sqlalchemy import or_
    
    # Query for prescriptions
    query = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.dispensed_by)
    )
    
    # Filter by status if provided
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            query = query.filter(Prescription.status == status_enum.value)
        except ValueError:
            pass
    else:
        # Default: show pending prescriptions
        query = query.filter(Prescription.status == OrderStatus.PENDING.value)
    
    # Search by patient name, patient number, or phone number
    if search:
        search_term = f"%{search.strip()}%"
        # For walk-in orders, patient_id is directly on Prescription (though prescriptions are usually encounter-based)
        # For encounter-based orders, patient is via Encounter
        query = query.outerjoin(Encounter).outerjoin(Patient, 
            or_(Prescription.patient_id == Patient.id, Encounter.patient_id == Patient.id)
        ).filter(
            or_(
                Patient.first_name.ilike(search_term),
                Patient.last_name.ilike(search_term),
                Patient.patient_number.ilike(search_term),
                Patient.phone_number.ilike(search_term),
                (Patient.first_name + ' ' + Patient.last_name).ilike(search_term)
            )
        )
    
    prescriptions = query.order_by(Prescription.prescribed_at.desc()).limit(100).all()
    
    # Check payment status for each prescription (for cash patients)
    from app.utils.payment_verification import is_cash_patient, check_payment_required_and_paid
    from app.models.billing_models import Charge, ChargeType, Invoice
    prescription_payment_status = {}
    
    for prescription in prescriptions:
        patient_id = None
        if prescription.encounter and prescription.encounter.patient:
            patient_id = prescription.encounter.patient.id
        elif prescription.patient_id:
            patient_id = prescription.patient_id
        
        if patient_id and is_cash_patient(db, patient_id):
            # Check if there's a charge for this prescription
            charge = db.query(Charge).filter(
                Charge.prescription_id == prescription.id,
                Charge.charge_type == ChargeType.PHARMACY,
                Charge.invoice.has(Invoice.is_active == True)
            ).first()
            
            if charge:
                invoice = charge.invoice
                try:
                    payment_required, payment_paid, _charge, _invoice = check_payment_required_and_paid(
                        db, patient_id, ChargeType.PHARMACY,
                        encounter_id=prescription.encounter_id,
                        prescription_id=prescription.id
                    )
                    if payment_required and not payment_paid:
                        prescription_payment_status[prescription.id] = {
                            "payment_required": True,
                            "invoice_id": invoice.id if invoice else None,
                            "balance": invoice.balance if invoice else None
                        }
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    # Don't 500 the dashboard; leave this prescription without payment-required flag
                    prescription_payment_status[prescription.id] = {
                        "payment_required": False,
                        "invoice_id": invoice.id if invoice else None,
                        "balance": invoice.balance if invoice else None
                    }
    
    context = {
        "request": request,
        "title": "Pharmacy (PhIS)",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescriptions": prescriptions,
        "prescription_payment_status": prescription_payment_status,
        "status_filter": status_filter,
        "search": search
    }
    return templates.TemplateResponse("ancillary/pharmacy_dashboard.html", context)


@router.get("/pharmacy/prescriptions/{prescription_id}", name="view_prescription")
def view_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"]))
):
    """
    View a specific prescription and dispense medication.
    """
    from app.crud import inventory_crud
    from app.crud import encounter_crud
    
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by),
        joinedload(Prescription.dispensed_by),
        joinedload(Prescription.medication)  # Eager load medication if linked
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient
    
    # Check inventory availability
    medication = None
    stock_check = None
    formulary_check = None
    stock_items = []
    
    # First, try to use medication_id if linked
    if prescription.medication_id and prescription.medication:
        medication = prescription.medication
    # Fallback to code lookup
    elif prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    # Fallback to name search
    if not medication:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    if medication:
        # Stock check
        required_quantity = prescription.quantity or 1
        stock_check = inventory_crud.check_stock_availability(db, medication.id, required_quantity)
        stock_items = inventory_crud.get_stock_items_by_medication(db, medication.id)
        
        # Formulary check
        formulary_check = inventory_crud.check_formulary_compliance(
            db, medication.id, patient.nhis_number
        )
        
        # Drug interaction check - get other active prescriptions for this patient
        other_prescriptions = db.query(Prescription).join(Encounter).filter(
            Encounter.patient_id == patient.id,
            Prescription.id != prescription_id,
            Prescription.status.in_([OrderStatus.PENDING.value, OrderStatus.ORDERED.value, OrderStatus.IN_PROGRESS.value])
        ).all()
        
        other_medication_ids = []
        for other_prescription in other_prescriptions:
            if other_prescription.medication_code:
                other_med = inventory_crud.get_medication_by_code(db, other_prescription.medication_code)
                if other_med:
                    other_medication_ids.append(other_med.id)
            else:
                other_meds = inventory_crud.get_medications(db, search=other_prescription.medication_name, limit=1)
                if other_meds:
                    other_medication_ids.append(other_meds[0].id)
        
        interaction_check = None
        if other_medication_ids:
            interaction_check = inventory_crud.check_drug_interactions(
                db, [medication.id] + other_medication_ids
            )
    else:
        interaction_check = None
    
    # Check payment status for cash patients
    from app.utils.payment_verification import (
        is_cash_patient,
        check_payment_required_and_paid,
        requires_payment_before_service
    )
    from app.models.billing_models import ChargeType
    from decimal import Decimal
    
    payment_required = False
    payment_paid = True
    payment_notice = None
    unpaid_invoice = None
    paid_invoice = None
    
    if is_cash_patient(db, patient.id):
        # First, ensure charge exists for this prescription (if not already created)
        # This allows us to always check payment status
        from app.services import create_charge_for_prescription
        try:
            create_charge_for_prescription(db, prescription, current_user.id, check_payment_required=False)
        except Exception as e:
            # Charge might already exist, continue
            pass
        
        # Check payment requirement and status
        payment_required = requires_payment_before_service(
            db, patient.id, ChargeType.PHARMACY
        )
        
        if payment_required:
            payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
                db, patient.id, ChargeType.PHARMACY,
                encounter_id=prescription.encounter_id,
                prescription_id=prescription_id
            )
            
            if invoice:
                if payment_paid:
                    paid_invoice = invoice
                    payment_notice = f"Payment Status: Patient has paid for this prescription. Invoice #{invoice.invoice_number} - Amount: GHS {invoice.total_amount:.2f}"
                else:
                    unpaid_invoice = invoice
                    payment_notice = f"Payment Required: Patient has not paid for this prescription. Outstanding balance: GHS {invoice.balance:.2f}"
            else:
                # Charge might not exist yet or still being created
                payment_notice = "Payment Status: Checking payment status..."
    
    context = {
        "request": request,
        "title": f"Prescription #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "medication": medication,
        "stock_check": stock_check,
        "formulary_check": formulary_check,
        "interaction_check": interaction_check,
        "stock_items": stock_items,
        "payment_required": payment_required,
        "payment_paid": payment_paid,
        "payment_notice": payment_notice,
        "unpaid_invoice": unpaid_invoice,
        "paid_invoice": paid_invoice
    }
    return templates.TemplateResponse("ancillary/prescription_detail.html", context)


@router.post("/pharmacy/prescriptions/{prescription_id}/dispense", name="dispense_prescription", status_code=status.HTTP_302_FOUND)
def dispense_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"])),
    stock_item_id: Optional[int] = Form(None)
):
    """
    Mark prescription as dispensed and update inventory.
    For cash patients: Checks if payment has been made before allowing dispensing.
    For IPD patients: Pharmacy charges are pay-as-you-go even if admitted.
    """
    from app.utils.payment_verification import (
        check_payment_required_and_paid,
        is_cash_patient
    )
    from app.models.billing_models import ChargeType
    from app.crud import inventory_crud
    from app.schemas.inventory_schemas import InventoryTransactionCreate
    from app.models.inventory_models import TransactionType
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Get patient from encounter
    encounter = prescription.encounter
    patient_id = encounter.patient_id
    
    # Create charge first (if it doesn't exist) for all patients
    # This ensures the charge exists before we check payment
    from app.services import create_charge_for_prescription
    try:
        # Create charge if it doesn't exist (function returns None if charge already exists)
        create_charge_for_prescription(db, prescription, current_user.id, check_payment_required=False)
    except Exception as e:
        # Log error but continue - charge might already exist
        print(f"Note: Charge creation for prescription {prescription_id}: {e}")
    
    # For cash patients: Check payment requirement before dispensing
    # Payment must be made before dispensing for cash patients
    # Note: For IPD patients, pharmacy is still pay-as-you-go
    if is_cash_patient(db, patient_id):
        # Now check if payment has been made
        payment_required, payment_paid, charge, invoice = check_payment_required_and_paid(
            db, patient_id, ChargeType.PHARMACY,
            encounter_id=encounter.id, prescription_id=prescription_id
        )
        
        if payment_required and not payment_paid:
            # Block dispensing - redirect back with payment required error
            invoice_id = invoice.id if invoice else None
            invoice_balance = invoice.balance if invoice else None
            return RedirectResponse(
                url=f"/pharmacy/prescriptions/{prescription_id}?error=payment_required&invoice_id={invoice_id}&balance={invoice_balance}",
                status_code=status.HTTP_302_FOUND
            )
    
    # Try to find medication - use medication_id first if linked
    medication = None
    if prescription.medication_id:
        medication = inventory_crud.get_medication(db, prescription.medication_id)
    elif prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    if not medication:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    # Update inventory if medication found
    if medication and stock_item_id:
        quantity = prescription.quantity or 1
        
        # Create sale transaction
        transaction_data = InventoryTransactionCreate(
            medication_id=medication.id,
            stock_item_id=stock_item_id,
            prescription_id=prescription_id,
            transaction_type=TransactionType.SALE,
            quantity=-quantity,  # Negative for sale
            notes=f"Dispensed for prescription #{prescription_id}"
        )
        inventory_crud.create_inventory_transaction(db, transaction_data, current_user.id)
    
    # Update prescription as dispensed
    # Payment check already performed above - if we reach here, payment is confirmed
    update_data = {
        "status": OrderStatus.COMPLETED.value,
        "dispensed_by_id": current_user.id,
        "dispensed_at": datetime.now()
    }
    
    prescription_update = PrescriptionUpdate(**update_data)
    updated_prescription = encounter_crud.update_prescription(db, prescription_id, prescription_update)
    
    # Charge is already created before dispensing (for cash patients) or will be created automatically
    # No need to create it again here since we create it earlier for payment verification
    
    # Redirect with success status
    return RedirectResponse(
        url=f"/pharmacy/prescriptions/{prescription_id}?status=dispensed",
        status_code=status.HTTP_302_FOUND
    )


@router.get("/pharmacy/prescriptions/{prescription_id}/print", name="print_prescription")
def print_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin", "Doctor", "Nurse", "Clinician"]))
):
    """Print prescription on receipt printer (especially when out of stock)"""
    from app.crud import hospital_settings_crud
    from app.crud import inventory_crud
    
    prescription = db.query(Prescription).options(
        joinedload(Prescription.encounter).joinedload(Encounter.patient),
        joinedload(Prescription.prescribed_by)
    ).filter(Prescription.id == prescription_id).first()
    
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    patient = prescription.encounter.patient
    
    # Get hospital settings for receipt header
    hospital_settings = hospital_settings_crud.get_hospital_settings(db)
    
    # Check stock availability
    medication = None
    stock_check = None
    if prescription.medication_code:
        medication = inventory_crud.get_medication_by_code(db, prescription.medication_code)
    
    if not medication and prescription.medication_name:
        medications = inventory_crud.get_medications(db, search=prescription.medication_name, limit=1)
        if medications:
            medication = medications[0]
    
    if medication:
        stock_check = inventory_crud.check_stock_availability(db, medication.id, prescription.quantity or 1)
    
    context = {
        "request": request,
        "title": f"Prescription #{prescription_id}",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "prescription": prescription,
        "patient": patient,
        "medication": medication,
        "stock_check": stock_check,
        "hospital_settings": hospital_settings
    }
    return templates.TemplateResponse("pharmacy/prescription_receipt.html", context)


@router.post("/pharmacy/prescriptions/{prescription_id}/cancel", name="cancel_prescription", status_code=status.HTTP_302_FOUND)
def cancel_prescription(
    request: Request,
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Pharmacy Staff", "Admin"])),
    reason: Optional[str] = Form(None)
):
    """
    Cancel a prescription when medication is not in stock.
    The prescription will still appear in patient records for audit purposes.
    """
    from app.models.encounter_models import OrderStatus
    from datetime import datetime
    
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Only allow cancellation if prescription is not already completed or cancelled
    if prescription.status == OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail="Cannot cancel a prescription that has already been dispensed"
        )
    
    if prescription.status == OrderStatus.CANCELLED:
        # Already cancelled, just redirect back
        return RedirectResponse(
            url=f"/pharmacy/prescriptions/{prescription_id}?status=already_cancelled",
            status_code=status.HTTP_302_FOUND
        )
    
    # Update prescription status to cancelled
    prescription.status = OrderStatus.CANCELLED
    prescription.updated_at = datetime.now()
    
    # Store cancellation reason in instructions if provided
    if reason:
        current_instructions = prescription.instructions or ""
        cancellation_note = f"\n\n[CANCELLED by {current_user.full_name or current_user.username} on {datetime.now().strftime('%Y-%m-%d %H:%M')}: {reason}]"
        prescription.instructions = current_instructions + cancellation_note
    else:
        current_instructions = prescription.instructions or ""
        cancellation_note = f"\n\n[CANCELLED by {current_user.full_name or current_user.username} on {datetime.now().strftime('%Y-%m-%d %H:%M')}: Medication not in stock]"
        prescription.instructions = current_instructions + cancellation_note
    
    db.commit()
    db.refresh(prescription)
    
    return RedirectResponse(
        url=f"/pharmacy/prescriptions/{prescription_id}?status=cancelled",
        status_code=status.HTTP_302_FOUND
    )


# Lab Result Print Route
@router.get("/lab/orders/{order_id}/print", name="print_lab_result")
def print_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin", "Doctor", "Nurse", "Clinician"]))
):
    """
    Print/Export lab result as PDF.
    """
    from app.models.lab_models import LabSample
    from app.models.lab_template_models import LabTemplate, LabReferenceRange
    from sqlalchemy.orm import joinedload
    
    lab_order = db.query(LabOrder).options(
        joinedload(LabOrder.encounter).joinedload(Encounter.patient),
        joinedload(LabOrder.ordered_by),
        joinedload(LabOrder.result_entered_by),
        joinedload(LabOrder.samples)
    ).filter(LabOrder.id == order_id).first()
    
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Get patient - handle both encounter-based and direct patient orders
    patient = None
    if lab_order.encounter and lab_order.encounter.patient:
        patient = lab_order.encounter.patient
    elif lab_order.patient_id:
        from app.models.patient_models import Patient
        patient = db.query(Patient).filter(Patient.id == lab_order.patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found for this lab order")
    
    # Get template and schema if available - use the same resolution as view_lab_order
    schema_json = None
    ref_ranges = {}
    # Use flags and reference ranges from the lab order if available, otherwise compute them
    flags_json = lab_order.flags_json if lab_order.flags_json else {}
    # Use stored reference ranges if available as base, but also compute to fill in missing values
    stored_ref_ranges = lab_order.reference_ranges_json if lab_order.reference_ranges_json else {}
    if stored_ref_ranges:
        ref_ranges = dict(stored_ref_ranges)  # Start with stored values
        print(f"DEBUG: Using stored reference ranges as base: {list(ref_ranges.keys())}")
    else:
        print("DEBUG: No stored reference ranges, will compute")
    print(f"DEBUG: lab_order.id={lab_order.id}, lab_test_id={lab_order.lab_test_id}, template_id={lab_order.template_id}")
    
    try:
        from app.services.lab_template_resolution import resolve_template_for_order
        from app.services.reference_range_engine import get_field_reference_range
        
        resolved = resolve_template_for_order(db, lab_order, persist=False)
        print(f"DEBUG: resolved={resolved}, schema_json type={type(resolved.schema_json) if resolved else None}")
        
        if resolved and resolved.schema_json:
            # Ensure schema_json is a dict, not a JSON string
            schema_json = resolved.schema_json
            if isinstance(schema_json, str):
                import json
                try:
                    schema_json = json.loads(schema_json)
                    print(f"DEBUG: Parsed schema_json from string to dict")
                except json.JSONDecodeError as e:
                    print(f"ERROR: Failed to parse schema_json string: {e}")
                    schema_json = None
            
            # Get reference ranges for each field
            if schema_json and patient:
                patient_age_days = None
                if patient.date_of_birth:
                    from datetime import date
                    today = date.today()
                    patient_age_days = (today - patient.date_of_birth).days
                
                print(f"DEBUG: patient.gender={patient.gender}, patient_age_days={patient_age_days}")
                print(f"DEBUG: schema fields={list(schema_json.get('fields', {}).keys())}")
                
                for fcode, fdef in (schema_json.get('fields') or {}).items():
                    # Handle numeric fields
                    if fdef.get('type') in ('numeric', 'integer'):
                        try:
                            range_result = get_field_reference_range(
                                db, fcode, 
                                patient_age_days, patient.gender or 'ANY', None
                            )
                            print(f"DEBUG: field={fcode}, range_result={range_result}")
                            if range_result:
                                # Use numeric values from database if available
                                ref_ranges[fcode] = {
                                    'low': float(range_result.low) if range_result.low else None,
                                    'high': float(range_result.high) if range_result.high else None,
                                    'critical_low': float(range_result.critical_low) if range_result.critical_low else None,
                                    'critical_high': float(range_result.critical_high) if range_result.critical_high else None,
                                    'unit': fdef.get('unit', '') or range_result.unit or '',
                                    'text_range': range_result.text_range,
                                    'sex': range_result.sex,
                                    'age_range': f"{range_result.age_min_days // 365 if range_result.age_min_days else 0}-{range_result.age_max_days // 365 if range_result.age_max_days else 'Adult'}" if range_result.age_min_days or range_result.age_max_days else None
                                }
                                # Special override for Trophozoites Count - ALWAYS use malaria density interpretation scale
                                # This ensures the correct reference range is always shown regardless of stored values
                                if fcode in ('trophozoite_count', 'TROPH_COUNT', 'parasite_density', 'PARASITE_DENSITY'):
                                    ref_ranges[fcode] = {
                                        'low': None,
                                        'high': None,
                                        'critical_low': None,
                                        'critical_high': None,
                                        'unit': 'Parasites/µL',
                                        'text_range': 'NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL',
                                        'sex': 'ANY',
                                        'age_range': None
                                    }
                                    print(f"DEBUG: print_lab_result - Overrode trophozoite_count reference range to malaria density scale")
                                # If numeric values are None, try to extract from template's reference_range
                                if ref_ranges[fcode]['low'] is None and ref_ranges[fcode]['high'] is None:
                                    template_ref = fdef.get('reference_range', {})
                                    if template_ref:
                                        # Check age applicability before using template values
                                        # Define age categories in days
                                        NEONATE_MAX_DAYS = 28       # 0-28 days
                                        CHILD_MAX_DAYS = 6570       # 0-18 years (approx 6570 days)
                                        ADULT_MIN_DAYS = 6570       # 18+ years
                                        ELDERLY_MIN_DAYS = 21900    # 60+ years (approx)
                                        
                                        is_age_appropriate = False
                                        if template_ref.get('all_ages', False):
                                            is_age_appropriate = True
                                        elif patient_age_days is not None:
                                            # Check specific age flags
                                            if patient_age_days <= NEONATE_MAX_DAYS and template_ref.get('applies_to_neonates', False):
                                                is_age_appropriate = True
                                            elif patient_age_days < ADULT_MIN_DAYS and template_ref.get('applies_to_children', False):
                                                is_age_appropriate = True
                                            elif patient_age_days >= ADULT_MIN_DAYS and template_ref.get('applies_to_adults', False):
                                                is_age_appropriate = True
                                            elif patient_age_days >= ELDERLY_MIN_DAYS and template_ref.get('applies_to_elderly', False):
                                                is_age_appropriate = True
                                        else:
                                            # No patient age - allow template if all_ages or no restrictions
                                            is_age_appropriate = template_ref.get('all_ages', True)
                                        
                                        if is_age_appropriate:
                                            # Try to get normal_value as low value, but only if it's a valid number
                                            normal_val = template_ref.get('normal_value')
                                            # Skip invalid values like "Not Seen", "Not Applicable", etc.
                                            if normal_val is not None and (isinstance(normal_val, (int, float)) or (isinstance(normal_val, str) and normal_val not in ['Not Seen', 'Not Applicable', 'N/A', 'None', ''])):
                                                try:
                                                    ref_ranges[fcode]['low'] = float(normal_val)
                                                    ref_ranges[fcode]['high'] = ref_ranges[fcode]['low']  # Same as low for single value
                                                except (ValueError, TypeError):
                                                    pass
                                            # Also preserve text_range from template - check both text_range and normal_range
                                            if not ref_ranges[fcode]['text_range']:
                                                template_text_range = template_ref.get('text_range') or template_ref.get('normal_range')
                                                # Skip invalid text ranges
                                                if template_text_range and template_text_range not in ['Not Seen', 'Not Applicable', 'N/A', 'None', '']:
                                                    ref_ranges[fcode]['text_range'] = template_text_range
                                            # Use template unit if none from database, but filter out invalid values
                                            if not ref_ranges[fcode]['unit']:
                                                template_unit = template_ref.get('units', '')
                                                # Don't use invalid unit values
                                                if template_unit and template_unit.upper() not in ['N/A', 'NONE', 'NOT APPLICABLE', 'NOT SEEN', '']:
                                                    ref_ranges[fcode]['unit'] = template_unit
                                        else:
                                            print(f"DEBUG: field={fcode}, template ref range skipped - not age appropriate for patient age {patient_age_days} days")
                        except Exception as rr_error:
                            print(f"Error getting reference range for {fcode}: {rr_error}")
                    # Handle non-numeric fields (select/qualitative) with text-based reference ranges
                    elif fdef.get('reference_range'):
                        # This handles qualitative/semi-quantitative fields like WIDAL tests
                        text_range = fdef.get('reference_range')
                        print(f"DEBUG: field={fcode}, text_reference_range={text_range}")
                        # Hide unit for qualitative tests (WIDAL, etc.) - don't show 'Titer' or 'None'
                        # Also check for units in the text_reference_range dict itself
                        # Filter out invalid unit values like 'N/A', 'None', 'Not Applicable', 'Not Seen'
                        invalid_units = ['none', 'titer', 'n/a', 'not applicable', 'not seen', '']
                        field_unit = fdef.get('unit', '') or ''
                        text_range_unit = text_range.get('units', '') if isinstance(text_range, dict) else ''
                        # Prefer field-level unit, but fall back to text_reference_range unit
                        display_unit = field_unit if field_unit and field_unit.lower() not in invalid_units else (text_range_unit if text_range_unit and text_range_unit.lower() not in invalid_units else '')
                        display_unit = '' if display_unit.lower() in invalid_units else display_unit
                        # Also filter text_range - if it's a string with invalid values, use it as text_range if valid
                        display_text_range = text_range
                        if isinstance(text_range, dict):
                            # For dict text_range, check for normal_range as alternative
                            display_text_range = text_range.get('text_range') or text_range.get('normal_range') or text_range
                            # If it's still a dict, use it as-is
                            if isinstance(display_text_range, dict):
                                display_text_range = text_range
                        # Filter out invalid text_range string values
                        if isinstance(display_text_range, str) and display_text_range.lower() in ['not seen', 'not applicable', 'n/a', 'none', '']:
                            display_text_range = None
                        ref_ranges[fcode] = {
                            'low': None,
                            'high': None,
                            'critical_low': None,
                            'critical_high': None,
                            'unit': display_unit,
                            'text_range': display_text_range,
                            'sex': fdef.get('sex', 'ANY'),
                            'age_range': fdef.get('age_range', None)
                        }
                
                # Special override for Trophozoites Count - ALWAYS use malaria density interpretation scale
                # This ensures the correct reference range is always shown regardless of stored values
                if fcode in ('trophozoite_count', 'TROPH_COUNT', 'parasite_density', 'PARASITE_DENSITY'):
                    ref_ranges[fcode] = {
                        'low': None,
                        'high': None,
                        'critical_low': None,
                        'critical_high': None,
                        'unit': 'Parasites/µL',
                        'text_range': 'NEG: 0 p/µL | LOW: 1-100 p/µL | MODERATE: 101-100,000 p/µL | SEVERE: >100,000 p/µL OR 10,000 with HB ≤5g/dL',
                        'sex': 'ANY',
                        'age_range': None
                    }
                    print(f"DEBUG: print_lab_result - Overrode trophozoite_count reference range to malaria density scale (non-numeric)")
        else:
            print("DEBUG: No schema resolved for this lab order")
    except Exception as e:
        print(f"Error resolving template for print: {e}")
        # Don't rollback here - let the outer handler do it
        schema_json = None  # Fall back to no schema
    
    print(f"DEBUG: Final ref_ranges={ref_ranges}")
    
    # Compute flags based on newly computed reference ranges
    # This ensures flags are accurate even if stored flags are outdated
    if ref_ranges and lab_order.result_json:
        try:
            from app.services.lab_result_validation import compute_flags
            
            # Build patient context for flag computation
            patient_context = {}
            if patient:
                patient_context["gender"] = patient.gender
                patient_context["date_of_birth"] = patient.date_of_birth
            
            # Compute flags using the schema and result
            if schema_json:
                computed_flags = compute_flags(db, schema_json, lab_order.result_json, patient_context)
                
                # Convert flags to the expected format
                if computed_flags:
                    flags_json = {}
                    for flag_info in computed_flags:
                        flags_json[flag_info.field_code] = {
                            "flag": flag_info.flag,
                            "value": flag_info.value,
                            "low": flag_info.low,
                            "high": flag_info.high,
                            "critical_low": flag_info.critical_low,
                            "critical_high": flag_info.critical_high
                        }
                    print(f"DEBUG: Computed {len(computed_flags)} flags from ref_ranges")
        except Exception as flag_err:
            print(f"Error computing flags: {flag_err}")
    
    # Get hospital settings
    from app.crud import hospital_settings_crud
    try:
        hospital_settings = hospital_settings_crud.get_hospital_settings(db)
        # If no settings exist, use default values
        if not hospital_settings:
            # Create a simple object with fallback values for the template
            import types
            hospital_settings = types.SimpleNamespace(
                hospital_name="DEI GRATIA MEDICAL SERVICES",
                hospital_address="North Dungu, Opposite Quantum Filling Station, Wayamba Junction, BLK A121, Tamale - Bolgatanga Road",
                hospital_phone="0546731001 / 0207642170",
                hospital_email="deigratiamsl@gmail.com",
                logo_url="/uploads/logos/hospital_logo.png",
                logo_path="uploads/logos/hospital_logo.png",
                lab_contact_email=None,
                lab_contact_phone=None,
                accreditation=None,
                accreditation_number=None
            )
    except Exception as e:
        print(f"Error getting hospital settings: {e}")
        # Create fallback object with required attributes
        import types
        hospital_settings = types.SimpleNamespace(
            hospital_name="DEI GRATIA MEDICAL SERVICES",
            hospital_address="North Dungu, Opposite Quantum Filling Station, Wayamba Junction, BLK A121, Tamale - Bolgatanga Road",
            hospital_phone="0546731001 / 0207642170",
            hospital_email="deigratiamsl@gmail.com",
            logo_url="/uploads/logos/hospital_logo.png",
            logo_path="uploads/logos/hospital_logo.png",
            lab_contact_email=None,
            lab_contact_phone=None,
            accreditation=None,
            accreditation_number=None
        )
    
    # Build context for PDF
    context = {
        "lab_order": lab_order,
        "patient": patient,
        "result_json": lab_order.result_json or {},
        "schema_json": schema_json,
        "flags_json": flags_json,
        "ref_ranges": ref_ranges,
        "hospital_settings": hospital_settings,
    }
    
    # Return HTML print view instead of PDF
    from datetime import datetime, timedelta
    from app.services.lab_template_schema import normalize_template_schema
    
    # Normalize schema to ensure consistent field lookups
    normalized_schema = normalize_template_schema(schema_json)
    
    # Calculate turnaround time
    turnaround_time = None
    if lab_order.ordered_at and lab_order.result_entered_at:
        delta = lab_order.result_entered_at - lab_order.ordered_at
        hours = delta.total_seconds() / 3600
        if hours < 24:
            turnaround_time = f"{int(hours)} hour(s)"
        else:
            days = hours / 24
            turnaround_time = f"{days:.1f} day(s)"
    
    return templates.TemplateResponse(
        "lab/print_lab_result.html",
        {
            "request": request,
            "lab_order": lab_order,
            "patient": patient,
            "result_json": lab_order.result_json or {},
            "schema_json": normalized_schema,
            "flags_json": flags_json,
            "ref_ranges": ref_ranges,
            "hospital_settings": hospital_settings,
            "samples": lab_order.samples,
            "now": datetime.now(),
            "turnaround_time": turnaround_time,
            "result_entered_by": lab_order.result_entered_by,
        }
    )


# Verify Lab Result Route
@router.post("/lab/orders/{order_id}/verify", name="verify_lab_result")
def verify_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"]))
):
    """
    Verify a lab result.
    """
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Update result status to VERIFIED
    lab_order.result_status = "VERIFIED"
    lab_order.updated_at = datetime.now()
    db.commit()
    
    return RedirectResponse(
        url=f"/api/v1/ancillary/lab/orders/{order_id}?status=verified",
        status_code=status.HTTP_302_FOUND
    )


# Authorize/Release Lab Result Route
@router.post("/lab/orders/{order_id}/authorize", name="authorize_lab_result")
def authorize_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"]))
):
    """
    Authorize/Release a lab result.
    """
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Update result status to RELEASED
    lab_order.result_status = "RELEASED"
    lab_order.updated_at = datetime.now()
    db.commit()
    
    return RedirectResponse(
        url=f"/api/v1/ancillary/lab/orders/{order_id}?status=released",
        status_code=status.HTTP_302_FOUND
    )


# Verify Lab Result Route
@router.post("/lab/orders/{order_id}/verify", name="verify_lab_result")
def verify_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"]))
):
    """
    Verify a lab result.
    """
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Update result status to VERIFIED
    lab_order.result_status = "VERIFIED"
    lab_order.updated_at = datetime.now()
    db.commit()
    
    return RedirectResponse(
        url=f"/api/v1/ancillary/lab/orders/{order_id}?status=verified",
        status_code=status.HTTP_302_FOUND
    )


# Authorize/Release Lab Result Route
@router.post("/lab/orders/{order_id}/authorize", name="authorize_lab_result")
def authorize_lab_result(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Lab Staff", "Admin"]))
):
    """
    Authorize/Release a lab result.
    """
    lab_order = db.query(LabOrder).filter(LabOrder.id == order_id).first()
    if not lab_order:
        raise HTTPException(status_code=404, detail="Lab order not found")
    
    # Update result status to RELEASED
    lab_order.result_status = "RELEASED"
    lab_order.updated_at = datetime.now()
    db.commit()
    
    return RedirectResponse(
        url=f"/api/v1/ancillary/lab/orders/{order_id}?status=released",
        status_code=status.HTTP_302_FOUND
    )

