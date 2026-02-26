#!/usr/bin/env python3
"""
Additional Ghana Lab Test Templates
=================================
This script adds commonly used lab test templates for Ghana hospitals:
- Stool Culture
- Urine Culture  
- Wound Swab/Culture
- Semen Analysis
- TB Tests (AFB Smear)
- Dengue Serology
- Hepatitis E
- Blood Transfusion Screening

All operations are idempotent (safe to re-run).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import json
import uuid
from datetime import datetime

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')


# Template definitions - using "choice" type for select fields
TEMPLATES = [
    {
        "name": "Lab Test - STOOL_CULTURE",
        "discipline": "Microbiology",
        "schema": {
            "fields": {
                "appearance": {
                    "type": "choice",
                    "label": "Appearance",
                    "options": ["Normal", "Watery", "Mucoid", "Bloody", "Mucoid-Bloody"],
                    "required": True
                },
                "consistency": {
                    "type": "choice",
                    "label": "Consistency",
                    "options": ["Formed", "Soft", "Liquid", "Semi-solid"],
                    "required": False
                },
                " occult_blood": {
                    "type": "choice",
                    "label": "Occult Blood",
                    "options": ["Negative", "Positive", "Trace"],
                    "required": False
                },
                "reducing_substances": {
                    "type": "choice",
                    "label": "Reducing Substances",
                    "options": ["Negative", "Positive"],
                    "required": False
                },
                "ph": {
                    "type": "numeric",
                    "label": "pH",
                    "unit": "",
                    "required": False
                },
                "stool_ova": {
                    "type": "choice",
                    "label": "Ova/Parasite",
                    "options": ["Not Seen", "Ascaris lumbricoides", "Hookworm", "Trichuris trichiura", "Giardia lamblia", "Entamoeba histolytica", "Taenia species"],
                    "required": False
                },
                "stool_cyst": {
                    "type": "choice",
                    "label": "Cysts",
                    "options": ["Not Seen", "Giardia lamblia", "Entamoeba histolytica", "Cryptosporidium"],
                    "required": False
                },
                "bacterial_growth": {
                    "type": "choice",
                    "label": "Bacterial Growth",
                    "options": ["No Growth", "Scanty", "Moderate", "Heavy"],
                    "required": False
                },
                "organism_1": {
                    "type": "text",
                    "label": "Organism Isolated 1",
                    "required": False
                },
                "organism_2": {
                    "type": "text",
                    "label": "Organism Isolated 2",
                    "required": False
                },
                "sensitivity_1": {
                    "type": "text",
                    "label": "Sensitivity Pattern 1",
                    "required": False
                },
                "sensitivity_2": {
                    "type": "text",
                    "label": "Sensitivity Pattern 2",
                    "required": False
                },
                "stool_comment": {
                    "type": "text",
                    "label": "Microbiologist Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - URINE_CULTURE",
        "discipline": "Microbiology",
        "schema": {
            "fields": {
                "appearance": {
                    "type": "choice",
                    "label": "Appearance",
                    "options": ["Clear", "Cloudy", "Turbid", "Bloody"],
                    "required": True
                },
                "wbc_field": {
                    "type": "numeric",
                    "label": "WBC Count",
                    "unit": "/HPF",
                    "required": False
                },
                "rbc_field": {
                    "type": "numeric",
                    "label": "RBC Count",
                    "unit": "/HPF",
                    "required": False
                },
                "epithelial_cells": {
                    "type": "numeric",
                    "label": "Epithelial Cells",
                    "unit": "/HPF",
                    "required": False
                },
                "bacteria": {
                    "type": "choice",
                    "label": "Bacteria",
                    "options": ["None Seen", "Few", "Moderate", "Many"],
                    "required": False
                },
                "culture_growth": {
                    "type": "choice",
                    "label": "Culture Growth",
                    "options": ["No Growth", "Mixed Growth", "Significant Growth", "Contaminant"],
                    "required": False
                },
                "isolate_1": {
                    "type": "text",
                    "label": "Isolate 1",
                    "required": False
                },
                "isolate_2": {
                    "type": "text",
                    "label": "Isolate 2",
                    "required": False
                },
                "colony_count": {
                    "type": "numeric",
                    "label": "Colony Count",
                    "unit": "CFU/mL",
                    "required": False
                },
                "antibiotic_1": {
                    "type": "choice",
                    "label": "Amoxicillin",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "antibiotic_2": {
                    "type": "choice",
                    "label": "Ciprofloxacin",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "antibiotic_3": {
                    "type": "choice",
                    "label": "Ceftriaxone",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "antibiotic_4": {
                    "type": "choice",
                    "label": "Nitrofurantoin",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "urine_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - WOUND_SWAB",
        "discipline": "Microbiology",
        "schema": {
            "fields": {
                "specimen_type": {
                    "type": "choice",
                    "label": "Specimen Type",
                    "options": ["Wound Swab", "Pus Swab", "Abscess Aspirate", "Ulcer Swab", "Surgical Wound"],
                    "required": True
                },
                "gram_stain": {
                    "type": "choice",
                    "label": "Gram Stain",
                    "options": ["No Organisms Seen", "Gram Positive Cocci", "Gram Negative Bacilli", "Gram Positive Bacilli", "Mixed Flora"],
                    "required": False
                },
                "wbc_grams": {
                    "type": "choice",
                    "label": "WBC on Gram Stain",
                    "options": ["None", "Few", "Moderate", "Many"],
                    "required": False
                },
                "culture_growth": {
                    "type": "choice",
                    "label": "Culture Growth",
                    "options": ["No Growth", "Mixed Growth", "Significant Growth", "Contaminant"],
                    "required": False
                },
                "organism": {
                    "type": "text",
                    "label": "Organism Isolated",
                    "required": False
                },
                "abs_sensitive": {
                    "type": "choice",
                    "label": "Amoxicillin/Clavulanate",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "cipro_sensitive": {
                    "type": "choice",
                    "label": "Ciprofloxacin",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "ceftri_sensitive": {
                    "type": "choice",
                    "label": "Ceftriaxone",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "clinda_sensitive": {
                    "type": "choice",
                    "label": "Clindamycin",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "metro_sensitive": {
                    "type": "choice",
                    "label": "Metronidazole",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "wound_comment": {
                    "type": "text",
                    "label": "Microbiologist Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - BLOOD_CULTURE",
        "discipline": "Microbiology",
        "schema": {
            "fields": {
                "collection_date": {
                    "type": "text",
                    "label": "Collection Date/Time",
                    "required": True
                },
                "incubation_time": {
                    "type": "numeric",
                    "label": "Incubation Time",
                    "unit": "hours",
                    "required": False
                },
                "growth_observed": {
                    "type": "choice",
                    "label": "Growth Observed",
                    "options": ["No Growth", "Growth at 24hrs", "Growth at 48hrs", "Growth after 48hrs"],
                    "required": False
                },
                "organism": {
                    "type": "text",
                    "label": "Organism Isolated",
                    "required": False
                },
                "gram_stain_result": {
                    "type": "choice",
                    "label": "Gram Stain",
                    "options": ["No Growth", "Gram Positive Cocci", "Gram Negative Bacilli", "Gram Positive Cocci in Chains", "Yeast"],
                    "required": False
                },
                "bc_sensitive_1": {
                    "type": "choice",
                    "label": "Antibiotic 1",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "bc_sensitive_2": {
                    "type": "choice",
                    "label": "Antibiotic 2",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "bc_sensitive_3": {
                    "type": "choice",
                    "label": "Antibiotic 3",
                    "options": ["Sensitive", "Resistant", "Intermediate", "Not Tested"],
                    "required": False
                },
                "blood_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - SEMEN_ANALYSIS",
        "discipline": "Andrology",
        "schema": {
            "fields": {
                "collection_method": {
                    "type": "choice",
                    "label": "Collection Method",
                    "options": [" Masturbation", "Sexual Intercourse", "Collected at Lab"],
                    "required": True
                },
                "collection_time": {
                    "type": "text",
                    "label": "Collection Time",
                    "required": False
                },
                "abstinence": {
                    "type": "numeric",
                    "label": "Days of Abstinence",
                    "unit": "days",
                    "required": False
                },
                "volume": {
                    "type": "numeric",
                    "label": "Volume",
                    "unit": "mL",
                    "required": True
                },
                "liquefaction": {
                    "type": "choice",
                    "label": "Liquefaction",
                    "options": ["Complete (<30 min)", "Incomplete (30-60 min)", "Delayed (>60 min)"],
                    "required": False
                },
                "appearance": {
                    "type": "choice",
                    "label": "Appearance",
                    "options": ["Grey-Opalescent", "Yellow", "Bloody", "Cloudy"],
                    "required": False
                },
                "ph_value": {
                    "type": "numeric",
                    "label": "pH",
                    "unit": "",
                    "required": True
                },
                "motility_1hr": {
                    "type": "numeric",
                    "label": "Motility at 1 hour",
                    "unit": "%",
                    "required": True
                },
                "motility_2hr": {
                    "type": "numeric",
                    "label": "Motility at 2 hours",
                    "unit": "%",
                    "required": False
                },
                "progressive": {
                    "type": "numeric",
                    "label": "Progressive Motility",
                    "unit": "%",
                    "required": False
                },
                "non_progressive": {
                    "type": "numeric",
                    "label": "Non-Progressive",
                    "unit": "%",
                    "required": False
                },
                "immotile": {
                    "type": "numeric",
                    "label": "Immotile",
                    "unit": "%",
                    "required": False
                },
                "sperm_count": {
                    "type": "numeric",
                    "label": "Sperm Count",
                    "unit": "million/mL",
                    "required": True
                },
                "total_sperm": {
                    "type": "numeric",
                    "label": "Total Sperm Count",
                    "unit": "million/ejaculate",
                    "required": False
                },
                "normal_forms": {
                    "type": "numeric",
                    "label": "Normal Forms",
                    "unit": "%",
                    "required": True
                },
                "head_defect": {
                    "type": "numeric",
                    "label": "Head Defects",
                    "unit": "%",
                    "required": False
                },
                "tail_defect": {
                    "type": "numeric",
                    "label": "Tail Defects",
                    "unit": "%",
                    "required": False
                },
                "agglutination": {
                    "type": "choice",
                    "label": "Agglutination",
                    "options": ["None", "Mild", "Moderate", "Severe"],
                    "required": False
                },
                "wbc_semen": {
                    "type": "numeric",
                    "label": "WBC",
                    "unit": "/HPF",
                    "required": False
                },
                "round_cells": {
                    "type": "numeric",
                    "label": "Round Cells",
                    "unit": "/HPF",
                    "required": False
                },
                "semen_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - TB_AFB",
        "discipline": "Microbiology",
        "schema": {
            "fields": {
                "specimen": {
                    "type": "choice",
                    "label": "Specimen Type",
                    "options": ["Sputum", "BAL", "Pleural Fluid", "Lymph Node Aspirate", "Urine", "CSF"],
                    "required": True
                },
                "collection_date": {
                    "type": "text",
                    "label": "Collection Date",
                    "required": True
                },
                "quality": {
                    "type": "choice",
                    "label": "Specimen Quality",
                    "options": ["Good (Mucoid)", "Blood-Stained", "Salivary", "Inadequate"],
                    "required": False
                },
                "afb_result": {
                    "type": "choice",
                    "label": "AFB Smear Result",
                    "options": ["Negative", "Scanty (1-9/100 fields)", "1+ (10-99/100 fields)", "2+ (1-10/field)", "3+ (>10/field)"],
                    "required": True
                },
                "afb_comments": {
                    "type": "text",
                    "label": "Comments",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - DENGUE_SEROLOGY",
        "discipline": "Serology",
        "schema": {
            "fields": {
                "dengue_ns1": {
                    "type": "choice",
                    "label": "Dengue NS1 Antigen",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": True
                },
                "dengue_igg": {
                    "type": "choice",
                    "label": "Dengue IgG",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": True
                },
                "dengue_igm": {
                    "type": "choice",
                    "label": "Dengue IgM",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": True
                },
                "dengue_result": {
                    "type": "choice",
                    "label": "Interpretation",
                    "options": ["Primary Infection", "Secondary Infection", "Negative", "Possible Recent"],
                    "required": False
                },
                "dengue_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - HEPATITIS_E",
        "discipline": "Serology",
        "schema": {
            "fields": {
                "hev_igm": {
                    "type": "choice",
                    "label": "HEV IgM",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": True
                },
                "hev_igg": {
                    "type": "choice",
                    "label": "HEV IgG",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": False
                },
                "hev_result": {
                    "type": "choice",
                    "label": "Interpretation",
                    "options": ["Acute Infection", "Past Infection", "No Evidence of Infection"],
                    "required": False
                },
                "hev_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - TRANSFUSION_SCREEN",
        "discipline": "Blood Bank",
        "schema": {
            "fields": {
                "blood_group": {
                    "type": "choice",
                    "label": "ABO Group",
                    "options": ["A", "B", "AB", "O"],
                    "required": True
                },
                "rhesus": {
                    "type": "choice",
                    "label": "Rhesus (D)",
                    "options": ["Positive", "Negative"],
                    "required": True
                },
                " ABO_reverse": {
                    "type": "choice",
                    "label": "ABO Reverse Group",
                    "options": ["A", "B", "AB", "O", "Not Done"],
                    "required": False
                },
                "antibody_screen": {
                    "type": "choice",
                    "label": "Antibody Screen",
                    "options": ["Negative", "Positive"],
                    "required": False
                },
                "direct_coombs": {
                    "type": "choice",
                    "label": "Direct Coombs Test",
                    "options": ["Negative", "Positive", "Weak Positive"],
                    "required": False
                },
                "hiv_result": {
                    "type": "choice",
                    "label": "HIV 1&2",
                    "options": ["Non-Reactive", "Reactive", "Indeterminate"],
                    "required": True
                },
                "hbsag_result": {
                    "type": "choice",
                    "label": "HBsAg",
                    "options": ["Negative", "Positive"],
                    "required": True
                },
                "hcv_result": {
                    "type": "choice",
                    "label": "HCV",
                    "options": ["Negative", "Positive"],
                    "required": True
                },
                "syphilis_result": {
                    "type": "choice",
                    "label": "Syphilis (VDRL)",
                    "options": ["Non-Reactive", "Reactive"],
                    "required": True
                },
                "malaria_result": {
                    "type": "choice",
                    "label": "Malaria RDT",
                    "options": ["Negative", "Positive"],
                    "required": True
                },
                "transfusion_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - MALARIA_RDT",
        "discipline": "Parasitology",
        "schema": {
            "fields": {
                "mp_result": {
                    "type": "choice",
                    "label": "Malaria RDT Result",
                    "options": ["Negative", "Positive - P. falciparum", "Positive - P. vivax", "Positive - Mixed"],
                    "required": True
                },
                "mp_control": {
                    "type": "choice",
                    "label": "Control Line",
                    "options": ["Valid", "Invalid"],
                    "required": True
                },
                "parasite_density": {
                    "type": "numeric",
                    "label": "Parasite Density (if done)",
                    "unit": "/μL",
                    "required": False
                },
                "mp_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - SCHISTOSOMIASIS",
        "discipline": "Parasitology",
        "schema": {
            "fields": {
                "s_sanguinis": {
                    "type": "choice",
                    "label": "S. haematobium Ova",
                    "options": ["Not Seen", "Seen - Few", "Seen - Moderate", "Seen - Many"],
                    "required": True
                },
                "s_mansoni": {
                    "type": "choice",
                    "label": "S. mansoni Ova",
                    "options": ["Not Seen", "Seen - Few", "Seen - Moderate", "Seen - Many"],
                    "required": True
                },
                "micro_hint": {
                    "type": "choice",
                    "label": "Microscopy Hint",
                    "options": ["Standard", "Concentration Technique"],
                    "required": False
                },
                "schisto_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - FILARIASIS",
        "discipline": "Parasitology",
        "schema": {
            "fields": {
                "microfilaria": {
                    "type": "choice",
                    "label": "Microfilaria",
                    "options": ["Not Seen", "Wuchereria bancrofti", "Brugia malayi", "Loa loa", "Mansonella perstans"],
                    "required": True
                },
                "filarian_nodule": {
                    "type": "choice",
                    "label": "Clinical Nodule",
                    "options": ["Absent", "Present"],
                    "required": False
                },
                "filariasis_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - SPUTUM_AFB",
        "discipline": "Microbiology",
        "schema": {
            "fields": {
                "sputum_quality": {
                    "type": "choice",
                    "label": "Sputum Quality",
                    "options": ["Adequate (Mucoid)", "Blood Stained", "Salivary", "Inadequate"],
                    "required": True
                },
                "afb_count": {
                    "type": "choice",
                    "label": "AFB Count",
                    "options": ["No AFB seen", "1-9/100 fields (Scanty)", "10-99/100 fields (1+)", "1-10/field (2+)", ">10/field (3+)"],
                    "required": True
                },
                "tb_diagnosis": {
                    "type": "choice",
                    "label": "Interpretation",
                    "options": ["No AFB Seen - MTD not detected", "Scanty - MTD detected", "Positive (1+) - MTD detected", "Positive (2+) - MTD detected", "Positive (3+) - MTD detected"],
                    "required": False
                },
                "sputum_comment": {
                    "type": "text",
                    "label": "Remark",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - HEPATITIS_A",
        "discipline": "Serology",
        "schema": {
            "fields": {
                "hav_igm": {
                    "type": "choice",
                    "label": "HAV IgM",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": True
                },
                "hav_total": {
                    "type": "choice",
                    "label": "HAV Total (IgM + IgG)",
                    "options": ["Negative", "Positive", "Equivocal"],
                    "required": False
                },
                "hav_result": {
                    "type": "choice",
                    "label": "Interpretation",
                    "options": ["Acute Hepatitis A", "Past Hepatitis A Infection", "No Evidence of Infection"],
                    "required": False
                },
                "hav_comment": {
                    "type": "text",
                    "label": "Comment",
                    "required": False
                }
            }
        }
    },
    {
        "name": "Lab Test - CYTOLOGY",
        "discipline": "Pathology",
        "schema": {
            "fields": {
                "specimen": {
                    "type": "choice",
                    "label": "Specimen Type",
                    "options": ["Pap Smear", "Fine Needle Aspirate", "Pleural Fluid", "Ascites", "Cervical Swab", "Other"],
                    "required": True
                },
                "adequacy": {
                    "type": "choice",
                    "label": "Sample Adequacy",
                    "options": ["Satisfactory", "Unsatisfactory - Inadequate", "Unsatisfactory - Bloodly"],
                    "required": True
                },
                "inflammatory": {
                    "type": "choice",
                    "label": "Inflammatory Cells",
                    "options": ["Nil", "Mild", "Moderate", "Severe"],
                    "required": False
                },
                "squamous": {
                    "type": "choice",
                    "label": "Squamous Epithelial Cells",
                    "options": ["Normal", "Atrophic", "Reactive Changes"],
                    "required": False
                },
                "glandular": {
                    "type": "choice",
                    "label": "Glandular Cells",
                    "options": ["Not Seen", "Endocervical", "Endometrial", "Columnar"],
                    "required": False
                },
                "cytology_result": {
                    "type": "choice",
                    "label": "Cytology Result",
                    "options": ["Negative for Intraepithelial Lesion or Malignancy (NILM)", "ASC-US", "ASC-H", "LSIL", "HSIL", "Squamous Cell Carcinoma", "Adenocarcinoma"],
                    "required": True
                },
                "infections": {
                    "type": "choice",
                    "label": "Infectious Agents",
                    "options": ["None Seen", "Trichomonas vaginalis", "Candida", "Bacterial Vaginosis", "Herpes"],
                    "required": False
                },
                "cytology_comment": {
                    "type": "text",
                    "label": "Pathologist Comment",
                    "required": False
                }
            }
        }
    }
]


def create_templates():
    """Create the additional lab templates."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        created_count = 0
        skipped_count = 0
        
        for template in TEMPLATES:
            name = template['name']
            
            # Check if template already exists
            check = conn.execute(text(f"""
                SELECT id FROM lab_templates WHERE name = '{name}'
            """))
            if check.fetchone():
                print(f"  Skipping: {name} (already exists)")
                skipped_count += 1
                continue
            
            # Create the template
            template_id = str(uuid.uuid4())
            version_id = str(uuid.uuid4())
            schema_json = json.dumps(template['schema'])
            
            conn.execute(text(f"""
                INSERT INTO lab_templates 
                (id, name, discipline, status, current_version, created_at, updated_at)
                VALUES 
                ('{template_id}', '{name}', '{template['discipline']}', 'active', 1, NOW(), NOW())
            """))
            
            conn.execute(text(f"""
                INSERT INTO lab_template_versions 
                (id, template_id, version, status, schema_json, created_at)
                VALUES 
                ('{version_id}', '{template_id}', 1, 'active', '{schema_json}', NOW())
            """))
            
            print(f"  Created: {name}")
            created_count += 1
        
        conn.commit()
    
    return created_count, skipped_count


def main():
    print("=" * 60)
    print("Creating Additional Ghana Lab Test Templates")
    print("=" * 60)
    print(f"\nDatabase: {DATABASE_URL}")
    print(f"Templates to create: {len(TEMPLATES)}")
    
    created, skipped = create_templates()
    
    print(f"\n{'=' * 60}")
    print(f"COMPLETED:")
    print(f"  - Created: {created} new templates")
    print(f"  - Skipped (already exist): {skipped}")
    print(f"{'=' * 60}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
