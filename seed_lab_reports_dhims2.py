#!/usr/bin/env python3
"""
DHIMS2-Compliant Lab Reports & Request Forms
=============================================
This script creates lab report templates that align with Ghana DHIMS2 requirements:
- Lab Request Form (paper-based printable)
- Lab Report Form (result slip)
- Summary Statistics for DHIMS2 reporting

All templates are designed to work with the existing lab module.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import json

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:password123@localhost:5433/lhims')


# DHIMS2 Lab Test Categories for reporting
DHIMS2_LAB_CATEGORIES = [
    {
        "code": "LAB001",
        "name": "Haematology",
        "tests": [
            "FBC", "Hb", "PCV", "ESR", "Retics", "Sickling", "Coombs", "Blood Group"
        ]
    },
    {
        "code": "LAB002", 
        "name": "Clinical Chemistry",
        "tests": [
            "LFT", "RFT", "Electrolytes", "Glucose", "Lipid Profile", "HbA1c", "OGTT"
        ]
    },
    {
        "code": "LAB003",
        "name": "Microbiology",
        "tests": [
            "Urine R/E", "Stool R/E", "Wound Swab", "Blood Culture", "Urine Culture", "Stool Culture"
        ]
    },
    {
        "code": "LAB004",
        "name": "Serology/Immunology",
        "tests": [
            "HIV", "HBsAg", "HCV", "VDRL", "TPHA", "Widal", "H. pylori"
        ]
    },
    {
        "code": "LAB005",
        "name": "Parasitology",
        "tests": [
            "Malaria RDT", "Malaria Film", "BF for MF", "Skin Snip", "Schistosomiasis"
        ]
    },
    {
        "code": "LAB006",
        "name": "Endocrinology",
        "tests": [
            "TSH", "FT3", "FT4", "Testosterone", "FSH", "LH", "Prolactin"
        ]
    },
    {
        "code": "LAB007",
        "name": "Tumor Markers",
        "tests": [
            "AFP", "PSA", "CEA", "CA-125", "CA-19-9", "Beta-HCG"
        ]
    },
    {
        "code": "LAB008",
        "name": "Other Specialized Tests",
        "tests": [
            "CD4", "Viral Load", "Semen Analysis", "Cytology", "Fluid Analysis"
        ]
    }
]


# Lab Request Form Template (for printing)
LAB_REQUEST_FORM = """
================================================================================
                            LABORATORY REQUEST FORM
================================================================================
Facility Name: _________________________  Facility Code: ________________________

Patient Name: __________________________  Age: _____  Sex: M / F

Patient ID: ___________________________  Contact: _____________________________

Ward/OPD: ____________________________  Date: ______________________________

================================================================================
                              TESTS REQUESTED (Tick)
================================================================================

[ ] HAEMATOLOGY
    [ ] Full Blood Count (FBC)      [ ] ESR          [ ] Sickling Test
    [ ] Blood Group & Rh           [ ] Coombs Test  [ ] Reticulocyte Count

[ ] CLINICAL CHEMISTRY
    [ ] Liver Function Tests       [ ] Lipid Profile    [ ] HbA1c
    [ ] Renal Function Tests      [ ] Electrolytes     [ ] OGTT
    [ ] Fasting Blood Sugar       [ ] Serum Protein

[ ] MICROBIOLOGY
    [ ] Urine R/E                 [ ] Stool R/E       [ ] Wound Swab
    [ ] Blood Culture             [ ] Urine Culture   [ ] Stool Culture

[ ] SEROLOGY/IMMUNOLOGY
    [ ] HIV Screening             [ ] HBsAg           [ ] HCV
    [ ] VDRL                      [ ] TPHA            [ ] Widal Test
    [ ] H. pylori                 [ ] ASO Titre      [ ] RA Factor
    [ ] CRP                       [ ] AFP             [ ] PSA

[ ] PARASITOLOGY
    [ ] Malaria RDT               [ ] Blood Film for MP
    [ ] BF for Microfilaria      [ ] Skin Snip

[ ] ENDOCRINE
    [ ] TSH                       [ ] FT3             [ ] FT4
    [ ] Testosterone              [ ] FSH/LH          [ ] Prolactin

[ ] OTHERS: ________________________________________________________________

================================================================================
                              CLINICAL NOTES
================================================================================
________________________________________________________________________________
________________________________________________________________________________
________________________________________________________________________________

Requested by: _________________________  Signature: ___________________________

================================================================================
                              FOR LAB USE ONLY
================================================================================
Sample Received: Date: __________ Time: _______  By: _________________________

Sample Type: _______________________  Quality: Good / Poor / Rejected

Results Ready: Date: _______________  Time: _______  Verified By: ___________

================================================================================
"""


# Lab Report Form Template (for printing)
LAB_REPORT_FORM = """
================================================================================
                            LABORATORY REPORT FORM
================================================================================
Facility Name: _________________________  Report Date: ________________________

Patient Name: __________________________  Patient ID: _________________________

Age: _____  Sex: M / F              Requesting Ward/OPD: ____________________

================================================================================
                            TEST RESULTS
================================================================================

TEST                              RESULT         UNIT        REFERENCE RANGE
--------------------------------------------------------------------------------
HAEMATOLOGY
Haemoglobin                      __________     g/dL        M: 13.0-17.0 / F: 12.0-15.0
PCV                              __________     %           M: 40-52 / F: 36-46
WBC Count                        __________     x10^9/L     4.0-11.0
Platelet Count                   __________     x10^9/L     150-400
MCV                              __________     fL          76-96

CLINICAL CHEMISTRY
Fasting Glucose                  __________     mmol/L      3.9-5.8
Total Cholesterol                __________     mmol/L      3.0-5.0
Creatinine                       __________     μmol/L      M: 62-115 / F: 44-97
ALT                              __________     U/L         M: 0-40 / F: 0-32
AST                              __________     U/L         M: 0-37 / F: 0-31

SEROLOGY
HIV Screening                    __________     Reactive / Non-Reactive
HBsAg                            __________     Positive / Negative
VDRL                            __________     Reactive / Non-Reactive

PARASITOLOGY
Malaria RDT                     __________     Positive / Negative
BF for MF                       __________     Present / Absent

================================================================================
                              LAB COMMENTS
________________________________________________________________________________
________________________________________________________________________________

Reported By: _____________________  Date: ___________________________________

Verified By: ______________________  Date: ___________________________________

================================================================================
"""


# DHIMS2 Monthly Lab Summary Template
DHIMS2_MONTHLY_SUMMARY = """
================================================================================
                    DHIMS2 MONTHLY LABORATORY SUMMARY REPORT
================================================================================
Facility Name: _________________________  Facility Code: ____________________

Month: _________________ Year: ___________  Reported By: ____________________

================================================================================
                         HAEMATOLOGY TESTS
--------------------------------------------------------------------------------
Test                                    Total Done      Positive     Negative
--------------------------------------------------------------------------------
Full Blood Count                       |______________|____________|____________|
Sickling Test                         |______________|____________|____________|
Blood Group & Rh                      |______________|____________|____________|
ESR                                    |______________|____________|____________|
Coombs Test                           |______________|____________|____________|

================================================================================
                      CLINICAL CHEMISTRY TESTS
--------------------------------------------------------------------------------
Test                                    Total Done      Abnormal    Normal
--------------------------------------------------------------------------------
Liver Function Tests                   |______________|____________|____________|
Renal Function Tests                  |______________|____________|____________|
Lipid Profile                         |______________|____________|____________|
Fasting Blood Sugar                   |______________|____________|____________|
HbA1c                                 |______________|____________|____________|

================================================================================
                        SEROLOGY TESTS
--------------------------------------------------------------------------------
Test                                    Total Done      Positive     Negative
--------------------------------------------------------------------------------
HIV Screening                          |______________|____________|____________|
HBsAg                                 |______________|____________|____________|
HCV Antibody                          |______________|____________|____________|
VDRL                                   |______________|____________|____________|
Widal Test                            |______________|____________|____________|

================================================================================
                       PARASITOLOGY TESTS
--------------------------------------------------------------------------------
Test                                    Total Done      Positive     Negative
--------------------------------------------------------------------------------
Malaria RDT                            |______________|____________|____________|
Malaria Blood Film                    |______________|____________|____________|
Stool R/E                             |______________|____________|____________|
Urine R/E                             |______________|____________|____________|

================================================================================
                      SPECIALIZED TESTS
--------------------------------------------------------------------------------
Test                                    Total Done      Abnormal    Normal
--------------------------------------------------------------------------------
CD4 Count                              |______________|____________|____________|
Viral Load (HIV)                      |______________|____________|____________|
Thyroid Function Tests                |______________|____________|____________|
Tumor Markers                        |______________|____________|____________|

================================================================================
                         SUMMARY STATISTICS
--------------------------------------------------------------------------------
Total Lab Tests Ordered This Month:     |_____________________________|
Total Patients Seen (Lab):             |_____________________________|
Tests per Patient Ratio:               |_____________________________|
Positive Results Rate:                 |_____________________________|
Critical Results Reported:              |_____________________________|
Rejected Samples:                      |_____________________________|

================================================================================
                         COMMENTS/CHALLENGES
________________________________________________________________________________
________________________________________________________________________________
________________________________________________________________________________

Reported By: _________________________  Date: ___________________________________

Approved By: _________________________  Date: ___________________________________

================================================================================
"""


def create_lab_reports():
    """Create lab report configurations in the database."""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        # Check if lab option sets exist
        result = conn.execute(text("SELECT code FROM lab_option_sets WHERE code = 'dhims2_categories'"))
        if not result.fetchone():
            # Insert DHIMS2 categories as option set
            categories_json = json.dumps(DHIMS2_LAB_CATEGORIES)
            conn.execute(text(f"""
                INSERT INTO lab_option_sets (code, options_json, created_at, updated_at)
                VALUES ('dhims2_categories', '{categories_json}', NOW(), NOW())
            """))
            print("  Created: dhims2_categories option set")
        else:
            print("  Skipping: dhims2_categories (already exists)")
        
        conn.commit()
    
    return True


def print_request_form():
    """Print the lab request form to stdout (can be saved as PDF)"""
    print(LAB_REQUEST_FORM)


def print_report_form():
    """Print the lab report form to stdout (can be saved as PDF)"""
    print(LAB_REPORT_FORM)


def print_monthly_summary():
    """Print the DHIMS2 monthly summary form"""
    print(DHIMS2_MONTHLY_SUMMARY)


def main():
    print("=" * 70)
    print("DHIMS2-Compliant Lab Reports & Forms Configuration")
    print("=" * 70)
    
    print("\n[1] Creating database configurations...")
    create_lab_reports()
    
    print("\n[2] === LAB REQUEST FORM ===")
    print_request_form()
    
    print("\n[3] === LAB REPORT FORM ===")
    print_report_form()
    
    print("\n[4] === DHIMS2 MONTHLY SUMMARY ===")
    print_monthly_summary()
    
    print("\n" + "=" * 70)
    print("COMPLETED")
    print("=" * 70)
    print("""
To use these forms:
1. Save the form text as PDF files for printing
2. Use them as templates in the lab module
3. Configure printing from the lab dashboard

The forms are designed for:
- Manual data entry (paper-based workflow)
- Scanning/OCR in the future
- Staff to fill in by hand
    """)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
