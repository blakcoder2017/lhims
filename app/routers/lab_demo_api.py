"""
Lab Template Demo API Routes

Development/testing routes for rendering lab templates without database.
"""
import json
import os
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from app.core.templates import templates

router = APIRouter(prefix="/lab", tags=["Lab Demo"])


@router.get("/demo/{schema_name}", name="lab_template_demo")
def lab_template_demo(
    request: Request,
    schema_name: str,
):
    """
    Render a template from a JSON schema file for development testing.
    
    Args:
        schema_name: Name of the schema file (without .json extension)
    
    This endpoint loads a schema from app/data/{schema_name}.json
    and renders it using the template macros.
    """
    # Load schema from file
    schema_path = Path(__file__).parent.parent / "data" / f"{schema_name}.json"
    
    if not schema_path.exists():
        raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found")
    
    try:
        with open(schema_path, 'r') as f:
            schema_json = json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON in schema: {str(e)}")
    
    # Extract schema parts
    meta = schema_json.get("meta", {})
    layout = schema_json.get("layout", {})
    sections = layout.get("sections", [])
    fields = schema_json.get("fields", {})
    
    # Mock reference ranges for demo
    ref_ranges = {}
    for field_id, field_def in fields.items():
        if field_def.get("type") == "numeric":
            code = field_def.get("code", field_id)
            # Create mock reference ranges
            if code == "Hb":
                ref_ranges[code] = {"low": 12.0, "high": 17.5, "unit": "g/dL"}
            elif code == "Hct":
                ref_ranges[code] = {"low": 36, "high": 50, "unit": "%"}
            elif code == "RBC":
                ref_ranges[code] = {"low": 4.0, "high": 6.0, "unit": "10^6/uL"}
            elif code == "WBC":
                ref_ranges[code] = {"low": 4.0, "high": 11.0, "unit": "10^3/uL"}
            elif code == "PLT":
                ref_ranges[code] = {"low": 150, "high": 400, "unit": "10^3/uL"}
    
    # Build context
    context = {
        "request": request,
        "title": f"Template Demo: {meta.get('name', schema_name)}",
        "template_name": meta.get("name", schema_name),
        "schema_json": schema_json,
        "meta": meta,
        "fields": fields,
        "layout": layout,
        "sections": sections,
        "result_json": {},
        "ref_ranges": ref_ranges,
        "flags_json": {},
        "option_sets": {},
    }
    
    return templates.TemplateResponse("lab/template_demo.html", context)


@router.get("/demo", name="lab_demo_list")
def lab_demo_list(request: Request):
    """List available demo schemas."""
    data_dir = Path(__file__).parent.parent / "data"
    
    schemas = []
    if data_dir.exists():
        for f in data_dir.glob("*.json"):
            schemas.append(f.stem)
    
    context = {
        "request": request,
        "title": "Lab Template Demos",
        "schemas": schemas,
    }
    
    return templates.TemplateResponse("lab/demo_list.html", context)
