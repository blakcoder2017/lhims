#!/usr/bin/env python3
"""
Comprehensive Reference Range Fix
================================
Adds all missing reference ranges for all template fields with proper
age and sex considerations.

This script adds:
1. All missing qualitative ranges (text options)
2. Sex-specific ranges where clinically appropriate  
3. Age-specific ranges for pediatric populations

Usage:
    python3 comprehensive_fix_reference_ranges.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+psycopg2://postgres:password123@localhost:5433/lhims')
engine = create_engine(DATABASE_URL)


def add_comprehensive_ranges():
    """Add all missing reference ranges."""
    
    # Comprehensive list of all missing reference ranges with proper age/sex considerations
    ranges = [
        # === BLOOD CULTURE ===
        ('bc_sensitive_1', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant,Intermediate,Not Tested'),
        ('bc_sensitive_2', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant,Intermediate,Not Tested'),
        ('bc_sensitive_3', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant,Intermediate,Not Tested'),
        ('blood_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('collection_date', 'ANY', 0, 36500, None, None, 'date', None, None, ''),
        ('gram_stain_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Gram Positive,Gram Negative,No Organism Seen'),
        ('growth_observed', 'ANY', 0, 36500, None, None, 'text', None, None, 'No Growth,Growth,Contaminated'),
        ('incubation_time', 'ANY', 0, 36500, None, None, 'hours', None, None, ''),
        
        # === CS_BLOOD ===
        ('gram_stain', 'ANY', 0, 36500, None, None, 'text', None, None, 'Gram Positive,Gram Negative,Mixed,No Bacteria Seen'),
        ('micrologist_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        
        # === CYTOLOGY ===
        ('adequacy', 'ANY', 0, 36500, None, None, 'text', None, None, 'Adequate,Inadequate,Satisfactory'),
        ('cytology_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('cytology_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Normal,Abnormal,Suspicious,Malignant'),
        ('glandular', 'ANY', 0, 36500, None, None, 'text', None, None, 'Present,Absent'),
        ('infections', 'ANY', 0, 36500, None, None, 'text', None, None, 'None,Ring,Trichomonas,Fungal'),
        ('inflammatory', 'ANY', 0, 36500, None, None, 'text', None, None, 'None,Mild,Moderate,Severe'),
        ('specimen', 'ANY', 0, 36500, None, None, 'text', None, None, 'Pap Smear,Fluid,Cytology Brush'),
        ('squamous', 'ANY', 0, 36500, None, None, 'text', None, None, 'Normal,Abnormal,ASCUS,LSIL,HSIL'),
        
        # === DENGUE SEROLOGY ===
        ('dengue_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('dengue_igg', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Equivocal,Positive'),
        ('dengue_igm', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Equivocal,Positive'),
        ('dengue_ns1', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Equivocal,Positive'),
        ('dengue_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Primary Infection,Secondary Infection'),
        
        # === FBC ===
        ('rbcmorph', 'ANY', 0, 36500, None, None, 'text', None, None, 'Normocytic,Hypochromic,Microcytic,Macrocytic'),
        ('remarks', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        
        # === FILARIASIS ===
        ('filarian_nodule', 'ANY', 0, 36500, None, None, 'text', None, None, 'Present,Absent'),
        ('filariasis_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        
        # === HEPATITIS A ===
        ('hav_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('hav_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive,Immune'),
        
        # === HEPATITIS E ===
        ('hev_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('hev_igg', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Equivocal,Positive'),
        ('hev_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive'),
        
        # === HIV SCREEN ===
        ('kit_name', 'ANY', 0, 36500, None, None, 'text', None, None, 'Determine,Unigold,Stat-Pak'),
        
        # === HVS RE ===
        ('culture', 'ANY', 0, 36500, None, None, 'text', None, None, 'No Growth,Normal Flora,Pathogen Isolated'),
        
        # === SCHISTOSOMIASIS ===
        ('micro_hint', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('s_mansoni', 'ANY', 0, 36500, None, None, 'text', None, None, 'Not Seen,Rare,Few,Many'),
        ('s_sanguinis', 'ANY', 0, 36500, None, None, 'text', None, None, 'Not Seen,Rare,Few,Many'),
        ('schisto_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        
        # === SEMEN ANALYSIS (comprehensive with sex-specific and age-appropriate ranges) ===
        ('abstinence', 'ANY', 18, 36500, 2, 7, 'days', None, None, None),
        ('agglutination', 'ANY', 18, 36500, 0, 10, '%', 0, None, None),
        ('collection_method', 'ANY', 18, 36500, None, None, 'text', None, None, 'masturbation,coitus interruptus,condom'),
        ('collection_time', 'ANY', 18, 36500, None, None, 'time', None, None, ''),
        ('head_defect', 'ANY', 18, 36500, 0, 30, '%', 0, None, None),
        ('immotile', 'ANY', 18, 36500, 0, 100, '%', 0, None, None),
        ('motility_1hr', 'M', 18, 36500, 40, 80, '%', 0, None, None),
        ('motility_2hr', 'M', 18, 36500, 30, 70, '%', 0, None, None),
        ('non_progressive', 'ANY', 18, 36500, 0, 20, '%', 0, None, None),
        ('ph_value', 'ANY', 18, 36500, 7.2, 8.0, 'pH', 7.0, 9.0, None),
        ('progressive', 'M', 18, 36500, 32, 100, '%', 0, None, None),
        ('round_cells', 'ANY', 18, 36500, 0, 5, 'million/mL', 0, None, None),
        ('semen_comment', 'ANY', 18, 36500, None, None, 'text', None, None, ''),
        ('tail_defect', 'ANY', 18, 36500, 0, 30, '%', 0, None, None),
        ('total_sperm', 'M', 18, 36500, 39, 200, 'million/ejaculate', 0, None, None),
        ('volume', 'M', 18, 36500, 1.5, 5.0, 'mL', 0.5, None, None),
        ('wbc_semen', 'ANY', 18, 36500, 0, 1, 'million/mL', 0, None, None),
        
        # === SKIN SNIP ===
        ('remarks', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        
        # === SPUTUM AFB ===
        ('afb_count', 'ANY', 0, 36500, 0, 100, 'per 100 fields', 0, None, None),
        ('sputum_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('sputum_quality', 'ANY', 0, 36500, None, None, 'text', None, None, 'Good,Acceptable,Poor'),
        ('tb_diagnosis', 'ANY', 0, 36500, None, None, 'text', None, None, 'TB Suspect,Confirmed TB,Not TB'),
        
        # === STOOL CULTURE ===
        ('occult_blood', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive'),
        ('bacterial_growth', 'ANY', 0, 36500, None, None, 'text', None, None, 'No Growth,Pathogen,Normal Flora'),
        ('organism_1', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('organism_2', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('reducing_substances', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive'),
        ('stool_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('stool_cyst', 'ANY', 0, 36500, None, None, 'text', None, None, 'Not Seen,Rare,Few,Many'),
        
        # === STOOL RE ===
        ('ova', 'ANY', 0, 36500, None, None, 'text', None, None, 'Not Seen,Rare,Few,Many'),
        ('parasites', 'ANY', 0, 36500, None, None, 'text', None, None, 'Not Seen,Rare,Few,Many'),
        
        # === TB AFB ===
        ('afb_comments', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('afb_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,1+,2+,3+,4+'),
        ('quality', 'ANY', 0, 36500, None, None, 'text', None, None, 'Satisfactory,Unsatisfactory'),
        
        # === TRANSFUSION SCREEN ===
        ('ABO_reverse', 'ANY', 0, 36500, None, None, 'text', None, None, 'A,B,AB,O'),
        ('antibody_screen', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive'),
        ('blood_group', 'ANY', 0, 36500, None, None, 'text', None, None, 'A,B,AB,O'),
        ('malaria_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive'),
        ('rhesus', 'ANY', 0, 36500, None, None, 'text', None, None, 'Positive,Negative'),
        ('syphilis_result', 'ANY', 0, 36500, None, None, 'text', None, None, 'Negative,Positive'),
        ('transfusion_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        
        # === URINE CULTURE ===
        ('antibiotic_1', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('antibiotic_2', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('antibiotic_3', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('antibiotic_4', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('bacteria', 'ANY', 0, 36500, None, None, 'text', None, None, 'None,Rare,Few,Moderate,Many'),
        ('colony_count', 'ANY', 0, 36500, 0, 100000, 'cfu/mL', 0, None, None),
        ('epithelial_cells', 'ANY', 0, 36500, 0, 10, '/HPF', 0, None, None),
        ('isolate_1', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('isolate_2', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('rbc_field', 'ANY', 0, 36500, 0, 10, '/HPF', 0, None, None),
        ('urine_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
        ('wbc_field', 'ANY', 0, 36500, 0, 20, '/HPF', 0, None, None),
        
        # === URINE RE ===
        ('casts', 'ANY', 0, 36500, None, None, 'text', None, None, 'None,Rare,Waxy,Granular,Hyaline'),
        ('urine_bacteria', 'ANY', 0, 36500, None, None, 'text', None, None, 'None,Rare,Few,Moderate,Many'),
        ('urine_crystals', 'ANY', 0, 36500, None, None, 'text', None, None, 'None,Rare,Calcium Oxalate,Urate,Phosphate'),
        
        # === WOUND SWAB ===
        ('abs_sensitive', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant'),
        ('ceftri_sensitive', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant'),
        ('cipro_sensitive', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant'),
        ('clinda_sensitive', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant'),
        ('gram_stain', 'ANY', 0, 36500, None, None, 'text', None, None, 'Gram Positive,Gram Negative,Mixed'),
        ('metro_sensitive', 'ANY', 0, 36500, None, None, 'text', None, None, 'Sensitive,Resistant'),
        ('specimen_type', 'ANY', 0, 36500, None, None, 'text', None, None, 'Pus,Swab,Tissue'),
        ('wbc_grams', 'ANY', 0, 36500, None, None, 'text', None, None, 'Few,Moderate,Many'),
        ('wound_comment', 'ANY', 0, 36500, None, None, 'text', None, None, ''),
    ]
    
    # Add sex-specific and age-specific ranges for key clinical parameters
    additional_clinical_ranges = [
        # === TSH - Add sex-specific and more age ranges ===
        ('tsh', 'M', 0, 28, 1.0, 39.0, 'mIU/L', 0.5, None),
        ('tsh', 'M', 28, 365, 1.0, 10.0, 'mIU/L', 0.5, None),
        ('tsh', 'M', 365, 2190, 0.7, 6.0, 'mIU/L', 0.5, None),
        ('tsh', 'M', 2190, 6570, 0.5, 5.0, 'mIU/L', 0.5, None),
        ('tsh', 'M', 6570, 25550, 0.4, 4.2, 'mIU/L', 0.5, 10.0),
        ('tsh', 'F', 0, 28, 1.0, 39.0, 'mIU/L', 0.5, None),
        ('tsh', 'F', 28, 365, 1.0, 10.0, 'mIU/L', 0.5, None),
        ('tsh', 'F', 365, 2190, 0.7, 6.0, 'mIU/L', 0.5, None),
        ('tsh', 'F', 2190, 6570, 0.5, 5.0, 'mIU/L', 0.5, None),
        ('tsh', 'F', 6570, 25550, 0.4, 4.2, 'mIU/L', 0.5, 10.0),
        
        # === FT3 - Add pediatric ranges ===
        ('ft3', 'M', 0, 28, 3.0, 8.0, 'pmol/L', None, None),
        ('ft3', 'M', 28, 365, 3.5, 7.5, 'pmol/L', None, None),
        ('ft3', 'M', 365, 6570, 3.5, 7.0, 'pmol/L', None, None),
        ('ft3', 'M', 6570, 25550, 4.0, 7.8, 'pmol/L', None, None),
        ('ft3', 'F', 0, 28, 3.0, 8.0, 'pmol/L', None, None),
        ('ft3', 'F', 28, 365, 3.5, 7.5, 'pmol/L', None, None),
        ('ft3', 'F', 365, 6570, 3.5, 7.0, 'pmol/L', None, None),
        ('ft3', 'F', 6570, 25550, 4.0, 7.8, 'pmol/L', None, None),
        
        # === FT4 - Add pediatric ranges ===
        ('ft4', 'M', 0, 28, 10.0, 28.0, 'pmol/L', None, None),
        ('ft4', 'M', 28, 365, 12.0, 26.0, 'pmol/L', None, None),
        ('ft4', 'M', 365, 6570, 12.0, 24.0, 'pmol/L', None, None),
        ('ft4', 'M', 6570, 25550, 12.0, 22.0, 'pmol/L', None, None),
        ('ft4', 'F', 0, 28, 10.0, 28.0, 'pmol/L', None, None),
        ('ft4', 'F', 28, 365, 12.0, 26.0, 'pmol/L', None, None),
        ('ft4', 'F', 365, 6570, 12.0, 24.0, 'pmol/L', None, None),
        ('ft4', 'F', 6570, 25550, 12.0, 22.0, 'pmol/L', None, None),
        
        # === Urea - Add sex-specific ranges ===
        ('urea', 'M', 0, 365, 1.8, 6.5, 'mmol/L', None, 35.7),
        ('urea', 'M', 365, 6570, 2.2, 7.0, 'mmol/L', None, 35.7),
        ('urea', 'M', 6570, 25550, 2.9, 8.2, 'mmol/L', None, 35.7),
        ('urea', 'F', 0, 365, 1.8, 6.0, 'mmol/L', None, 35.7),
        ('urea', 'F', 365, 6570, 2.0, 6.5, 'mmol/L', None, 35.7),
        ('urea', 'F', 6570, 25550, 2.5, 7.5, 'mmol/L', None, 35.7),
        
        # === Cortisol - Add age-specific ===
        ('cortisol_value', 'ANY', 0, 365, 80, 580, 'nmol/L', 50, None),
        ('cortisol_value', 'ANY', 365, 6570, 80, 500, 'nmol/L', 50, None),
        ('cortisol_value', 'ANY', 6570, 25550, 140, 500, 'nmol/L', 50, None),
        
        # === DHEA ===
        ('dhea_value', 'M', 0, 365, 0.2, 1.2, 'μmol/L', None, None),
        ('dhea_value', 'M', 365, 6570, 0.4, 2.5, 'μmol/L', None, None),
        ('dhea_value', 'M', 6570, 12775, 5.0, 25.0, 'μmol/L', None, None),
        ('dhea_value', 'M', 12775, 25550, 2.5, 15.0, 'μmol/L', None, None),
        ('dhea_value', 'F', 0, 365, 0.2, 1.0, 'μmol/L', None, None),
        ('dhea_value', 'F', 365, 6570, 0.3, 2.0, 'μmol/L', None, None),
        ('dhea_value', 'F', 6570, 12775, 3.0, 15.0, 'μmol/L', None, None),
        ('dhea_value', 'F', 12775, 25550, 1.0, 10.0, 'μmol/L', None, None),
    ]
    
    all_ranges = ranges + additional_clinical_ranges
    
    with engine.connect() as conn:
        added = 0
        for range_data in all_ranges:
            try:
                conn.execute(text("""
                    INSERT INTO lab_reference_ranges 
                    (field_code, sex, age_min_days, age_max_days, low, high, unit, critical_low, critical_high, text_range)
                    VALUES (:field_code, :sex, :age_min, :age_max, :low, :high, :unit, :critical_low, :critical_high, :text_range)
                    ON CONFLICT DO NOTHING
                """), {
                    'field_code': range_data[0],
                    'sex': range_data[1],
                    'age_min': range_data[2],
                    'age_max': range_data[3],
                    'low': range_data[4],
                    'high': range_data[5],
                    'unit': range_data[6],
                    'critical_low': range_data[7],
                    'critical_high': range_data[8],
                    'text_range': range_data[9] if len(range_data) > 9 else None
                })
                added += 1
            except Exception as e:
                print(f"Error adding {range_data[0]}: {e}")
        
        conn.commit()
        print(f"Added {added} reference ranges")


def main():
    print("="*60)
    print("COMPREHENSIVE REFERENCE RANGE FIX")
    print("="*60)
    add_comprehensive_ranges()
    print("\nDone!")


if __name__ == "__main__":
    main()
