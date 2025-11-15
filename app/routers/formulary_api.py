from fastapi import APIRouter, Depends, HTTPException, Request, Form, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import Optional

from app.db.database import get_db
from app.core.deps import get_current_user, role_required
from app.models.inventory_models import FormularyRule, DrugInteraction, Medication
from app.crud import inventory_crud
from app.schemas.inventory_schemas import FormularyRuleCreate, DrugInteractionCreate

router = APIRouter(tags=["Formulary"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/pharmacy/formulary", name="formulary_dashboard")
def formulary_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Formulary rules management dashboard"""
    rules = db.query(FormularyRule).options(
        joinedload(FormularyRule.medication)
    ).filter(FormularyRule.is_active == True).order_by(FormularyRule.created_at.desc()).limit(100).all()
    
    context = {
        "request": request,
        "title": "Formulary Rules Management",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "rules": rules
    }
    return templates.TemplateResponse("inventory/formulary_dashboard.html", context)


@router.post("/pharmacy/formulary/create", name="create_formulary_rule", status_code=302)
def create_formulary_rule(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    rule_name: str = Form(...),
    rule_type: str = Form(...),
    description: Optional[str] = Form(None),
    medication_id: Optional[int] = Form(None),
    medication_category: Optional[str] = Form(None),
    condition: Optional[str] = Form(None)
):
    """Create a formulary rule"""
    rule_data = FormularyRuleCreate(
        rule_name=rule_name,
        rule_type=rule_type,
        description=description,
        medication_id=medication_id,
        medication_category=medication_category,
        condition=condition
    )
    
    rule = inventory_crud.create_formulary_rule(db, rule_data)
    return RedirectResponse(url="/pharmacy/formulary?status=created", status_code=302)


@router.get("/pharmacy/drug-interactions", name="drug_interactions_dashboard")
def drug_interactions_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"]))
):
    """Drug interactions database management dashboard"""
    interactions = db.query(DrugInteraction).options(
        joinedload(DrugInteraction.medication1),
        joinedload(DrugInteraction.medication2)
    ).order_by(DrugInteraction.created_at.desc()).limit(100).all()
    
    medications = inventory_crud.get_medications(db, limit=200)
    
    context = {
        "request": request,
        "title": "Drug Interactions Database",
        "current_user": current_user,
        "user_role": current_user.role.name,
        "interactions": interactions,
        "medications": medications
    }
    return templates.TemplateResponse("inventory/drug_interactions_dashboard.html", context)


@router.post("/pharmacy/drug-interactions/create", name="create_drug_interaction", status_code=302)
def create_drug_interaction(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(role_required(["Admin", "Pharmacy Staff"])),
    medication1_id: int = Form(...),
    medication2_id: int = Form(...),
    interaction_type: str = Form(...),
    severity: str = Form(...),
    description: str = Form(...),
    clinical_significance: Optional[str] = Form(None),
    management: Optional[str] = Form(None)
):
    """Create a drug interaction record"""
    interaction_data = DrugInteractionCreate(
        medication1_id=medication1_id,
        medication2_id=medication2_id,
        interaction_type=interaction_type,
        severity=severity,
        description=description,
        clinical_significance=clinical_significance,
        management=management
    )
    
    interaction = inventory_crud.create_drug_interaction(db, interaction_data)
    return RedirectResponse(url="/pharmacy/drug-interactions?status=created", status_code=302)

