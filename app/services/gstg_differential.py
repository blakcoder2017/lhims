from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass
class STGEntry:
    diagnosis: str
    body_system: str
    stg_reference: str
    stg_summary: str
    keywords: List[str]
    flags: List[str]
    age_bias: Optional[Dict[str, int]] = None  # {"min": 0, "max": 5}
    sex_bias: Optional[str] = None  # "male" / "female"


G_STG_LIBRARY: List[STGEntry] = [
    STGEntry(
        diagnosis="Severe Malaria",
        body_system="Infectious Diseases",
        stg_reference="Chapter 3 • Section 3.2",
        stg_summary="Test with malaria RDT/microscopy. Initiate parenteral artesunate, manage hypoglycaemia, treat anaemia, monitor fluids.",
        keywords=["fever", "rigor", "chills", "anemia", "parasite", "plasmodium", "malaria", "travel", "mosquito"],
        flags=["urgent", "infectious"]
    ),
    STGEntry(
        diagnosis="Community-Acquired Pneumonia",
        body_system="Respiratory",
        stg_reference="Chapter 5 • Section 5.1",
        stg_summary="Evaluate respiratory rate, oxygen saturation, chest exam. Start empirical antibiotics per age/severity and ensure oxygen/fluids as needed.",
        keywords=["cough", "productive", "dyspnea", "shortness of breath", "crepitations", "infiltrate", "sputum", "pleuritic"],
        flags=["urgent"]
    ),
    STGEntry(
        diagnosis="Acute Exacerbation of Asthma",
        body_system="Respiratory",
        stg_reference="Chapter 5 • Section 5.3",
        stg_summary="Assess peak flow, give inhaled/nebulized salbutamol, add steroids, provide oxygen, consider admission if poor response.",
        keywords=["wheeze", "asthma", "tight chest", "trigger", "nocturnal cough"],
        flags=["urgent"],
        age_bias={"min": 5}
    ),
    STGEntry(
        diagnosis="Hypertensive Emergency",
        body_system="Cardiovascular",
        stg_reference="Chapter 7 • Section 7.4",
        stg_summary="If BP ≥180/120 with end-organ damage symptoms, admit, start IV antihypertensives, monitor closely, adjust chronic meds.",
        keywords=["headache", "blurred vision", "bp", "hypertension", "stroke", "renal", "proteinuria"],
        flags=["needs urgent review"],
        age_bias={"min": 30}
    ),
    STGEntry(
        diagnosis="Diabetic Ketoacidosis",
        body_system="Endocrine",
        stg_reference="Chapter 8 • Section 8.2",
        stg_summary="Check random glucose, ketones, ABG. Start IV fluids, insulin infusion, potassium monitoring, treat trigger.",
        keywords=["polyuria", "polydipsia", "kussmaul", "acetone", "hyperglycemia", "ketones", "weight loss"],
        flags=["urgent"],
        age_bias={"min": 8}
    ),
    STGEntry(
        diagnosis="Typhoid Fever",
        body_system="Infectious Diseases",
        stg_reference="Chapter 3 • Section 3.5",
        stg_summary="Consider prolonged fever with abdominal pain, relative bradycardia. Request blood culture/Widal, start ceftriaxone or azithromycin.",
        keywords=["fever", "abdominal pain", "rose spots", "constipation", "bradycardia", "travel", "contaminated water"],
        flags=["infectious"]
    ),
    STGEntry(
        diagnosis="Obstetric Haemorrhage",
        body_system="Obstetrics",
        stg_reference="Chapter 11 • Section 11.4",
        stg_summary="Assess pregnancy status, quantify bleeding, resuscitate, give oxytocin/misoprostol, prepare for referral or theatre.",
        keywords=["pregnant", "gravida", "bleeding", "uterine", "postpartum", "labour"],
        flags=["obstetric emergency"],
        sex_bias="female",
        age_bias={"min": 12, "max": 55}
    ),
]


def _normalize_text(*parts: Optional[str]) -> str:
    combined = " ".join(filter(None, [p.strip() for p in parts if p]))
    combined = combined.lower()
    combined = re.sub(r"[^a-z0-9\s\.]", " ", combined)
    combined = re.sub(r"\s+", " ", combined)
    return combined.strip()


def _score_entry(entry: STGEntry, text: str, age: Optional[int], sex: Optional[str]) -> float:
    score = 0.0
    for kw in entry.keywords:
        if kw in text:
            score += 1.0
    if not score:
        # allow small baseline if keywords partially present as individual tokens
        tokens = text.split()
        overlap = {kw for kw in entry.keywords if kw.split()[0] in tokens}
        if overlap:
            score += 0.4
    if entry.age_bias and age is not None:
        min_age = entry.age_bias.get("min")
        max_age = entry.age_bias.get("max")
        if min_age is not None and age < min_age:
            score *= 0.6
        elif max_age is not None and age > max_age:
            score *= 0.6
        else:
            score *= 1.1
    if entry.sex_bias and sex:
        if sex.lower().startswith(entry.sex_bias.lower()[:1]):
            score *= 1.15
        else:
            score *= 0.5
    return round(score, 3)


def generate_differential_suggestions(
    clinical_summary: str,
    age: Optional[int] = None,
    sex: Optional[str] = None,
    key_vitals: Optional[str] = None,
    key_labs: Optional[str] = None,
    limit: int = 6
) -> List[Dict]:
    """
    Return ranked Ghana STG differential suggestions based on summary text.
    """
    normalized = _normalize_text(clinical_summary, key_vitals, key_labs)
    suggestions: List[Dict] = []
    for entry in G_STG_LIBRARY:
        relevance = _score_entry(entry, normalized, age, sex)
        if relevance <= 0:
            continue
        suggestions.append({
            "diagnosis": entry.diagnosis,
            "body_system": entry.body_system,
            "stg_reference": entry.stg_reference,
            "stg_summary": entry.stg_summary,
            "relevance_score": relevance,
            "flags": entry.flags,
            "status": "suggested"
        })
    if not suggestions:
        # fallback to top 3 library entries
        fallback = [{
            "diagnosis": entry.diagnosis,
            "body_system": entry.body_system,
            "stg_reference": entry.stg_reference,
            "stg_summary": entry.stg_summary,
            "relevance_score": 0.3,
            "flags": entry.flags,
            "status": "suggested"
        } for entry in G_STG_LIBRARY[:3]]
        suggestions.extend(fallback)
    suggestions.sort(key=lambda s: s["relevance_score"], reverse=True)
    trimmed = suggestions[:limit]
    for idx, suggestion in enumerate(trimmed, start=1):
        suggestion.setdefault("rank", idx)
    return trimmed


