"""
Seed script to add DHIS2 mappings to existing diseases.

This script updates diseases in the database with DHIS2 data element UIDs
for Ghana DHIMS2 reporting. The UIDs should be obtained from your local
DHIS2 instance and updated as needed.

Note: DHIS2 data element UIDs are specific to each DHIS2 instance.
These mappings are based on common Ghana DHIMS2 configurations but
may need to be customized for your specific implementation.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()
db_url = os.getenv("SQLALCHEMY_DATABASE_URL")

if not db_url:
    print("Error: SQLALCHEMY_DATABASE_URL not found in environment")
    sys.exit(1)

print(f"Using database: {db_url[:50]}...")

# Use raw SQL with psycopg2
import psycopg2
from psycopg2 import sql

# Connect to database
db_url_for_psycopg2 = db_url.replace('postgresql+psycopg2://', 'postgresql://')
conn = psycopg2.connect(db_url_for_psycopg2)
conn.autocommit = False
cursor = conn.cursor()

# DHIMS2 Data Element Mappings for common Ghana diseases
# These UIDs should be configured based on your DHIS2 instance
# Format: {disease_name_lowercase: (dhis2_uid, category_option_combo_uid, category)}
DHIS2_MAPPINGS = {
    # INFECTIOUS DISEASES
    "cholera": ("xyzCholera01", "male_5plus", "infectious"),
    "unspecified cholera": ("xyzCholera01", "female_5plus", "infectious"),
    "typhoid fever": ("xyzTyphoid01", None, "infectious"),
    "amoebiasis": ("xyzAmoebiasis01", None, "infectious"),
    "shigellosis": ("xyzShigellosis01", None, "infectious"),
    "diarrhea without dehydration": ("xyzDiarrhea01", "none", "infectious"),
    "diarrhea with moderate dehydration": ("xyzDiarrhea02", "moderate", "infectious"),
    "diarrhea with severe dehydration": ("xyzDiarrhea03", "severe", "infectious"),
    
    # Viral Diseases
    "measles": ("xyzMeasles01", None, "infectious"),
    "rubella": ("xyzRubella01", None, "infectious"),
    "yellow fever": ("xyzYellowFever01", None, "infectious"),
    "viral hepatitis a": ("xyzHepA01", None, "infectious"),
    "viral hepatitis b": ("xyzHepB01", None, "infectious"),
    "viral hepatitis c": ("xyzHepC01", None, "infectious"),
    "viral hepatitis e": ("xyzHepE01", None, "infectious"),
    "hiv/aids": ("xyzHIV01", None, "infectious"),
    "human immunodeficiency virus (hiv)": ("xyzHIV01", None, "infectious"),
    "covid-19": ("xyzCovid01", None, "infectious"),
    
    # Influenza
    "influenza": ("xyzInfluenza01", None, "infectious"),
    "influenza with pneumonia": ("xyzInfluenza02", None, "infectious"),
    "influenza with other respiratory manifestations": ("xyzInfluenza03", None, "infectious"),
    
    # Vector-borne Diseases
    "malaria (uncomplicated)": ("xyzMalaria01", "uncomplicated", "infectious"),
    "severe malaria": ("xyzMalaria02", "severe", "infectious"),
    "malaria with cerebral complications": ("xyzMalaria03", "cerebral", "infectious"),
    "malaria with severe anemia": ("xyzMalaria04", "severe_anemia", "infectious"),
    "onchocerciasis": ("xyzOncho01", None, "infectious"),
    "schistosomiasis": ("xyzSchisto01", None, "infectious"),
    "lymphatic filariasis": ("xyzFilariasis01", None, "infectious"),
    "dengue fever": ("xyzDengue01", None, "infectious"),
    "chikungunya": ("xyzChikV01", None, "infectious"),
    
    # Tuberculosis
    "pulmonary tuberculosis (new)": ("xyzTB01", "new_case", "infectious"),
    "pulmonary tuberculosis (relapse)": ("xyzTB02", "relapse", "infectious"),
    "extra-pulmonary tuberculosis": ("xyzTB03", "eptb", "infectious"),
    "tuberculous meningitis": ("xyzTB04", "meningitis", "infectious"),
    "tuberculosis of lymph nodes": ("xyzTB05", "lymph_node", "infectious"),
    "tuberculosis of bones and joints": ("xyzTB06", "bone_joint", "infectious"),
    "miliary tuberculosis": ("xyzTB07", "miliary", "infectious"),
    "drug-resistant tb (dr-tb)": ("xyzTB08", "dr", "infectious"),
    
    # Bacterial Infections
    "meningitis (bacterial)": ("xyzMening01", "bacterial", "infectious"),
    "meningococcal meningitis": ("xyzMening02", "meningococcal", "infectious"),
    "pneumococcal meningitis": ("xyzMening03", "pneumococcal", "infectious"),
    "meningitis (unspecified)": ("xyzMening04", "unspecified", "infectious"),
    "sepsis": ("xyzSepsis01", None, "infectious"),
    "neonatal sepsis": ("xyzNeoSepsis01", None, "infectious"),
    "tetanus": ("xyzTetanus01", None, "infectious"),
    "neonatal tetanus": ("xyzNeoTet01", None, "infectious"),
    "diphtheria": ("xyzDiphtheria01", None, "infectious"),
    "whooping cough (pertussis)": ("xyzPertussis01", None, "infectious"),
    "acute poliomyelitis": ("xyzPolio01", None, "infectious"),
    "leprosy": ("xyzLeprosy01", None, "infectious"),
    "buruli ulcer": ("xyzBuruli01", None, "infectious"),
    "yaws": ("xyzYaws01", None, "infectious"),
    " guinea worm (dracunculiasis)": ("xyzGuineaWorm01", None, "infectious"),
    
    # NON-COMMUNICABLE DISEASES
    "hypertension": ("xyzHypertension01", None, "ncd"),
    "hypertensive heart disease": ("xyzHypertension02", "heart", "ncd"),
    "diabetes mellitus": ("xyzDiabetes01", None, "ncd"),
    "diabetes with ketoacidosis": ("xyzDiabetes02", "ketoacidosis", "ncd"),
    "diabetes with nephropathy": ("xyzDiabetes03", "nephropathy", "ncd"),
    "diabetes with retinopathy": ("xyzDiabetes04", "retinopathy", "ncd"),
    "asthma": ("xyzAsthma01", None, "ncd"),
    "chronic obstructive pulmonary disease": ("xyzCOPD01", None, "ncd"),
    "cancer of breast": ("xyzCancer01", "breast", "ncd"),
    "cancer of cervix": ("xyzCancer02", "cervix", "ncd"),
    "cancer of prostate": ("xyzCancer03", "prostate", "ncd"),
    "cancer of liver": ("xyzCancer04", "liver", "ncd"),
    "cancer of lung": ("xyzCancer05", "lung", "ncd"),
    "cancer (other)": ("xyzCancer99", "other", "ncd"),
    "sickle cell disease": ("xyzSickleCell01", None, "ncd"),
    "epilepsy": ("xyzEpilepsy01", None, "ncd"),
    "chronic kidney disease": ("xyzKidney01", None, "ncd"),
    
    # MATERNAL CONDITIONS
    "maternal death": ("xyzMaternalDeath01", None, "maternal"),
    "maternal near miss": ("xyzMaternalNearMiss01", None, "maternal"),
    "obstructed labor": ("xyzObstructedLabor01", None, "maternal"),
    "uterine rupture": ("xyzUterineRupture01", None, "maternal"),
    "postpartum hemorrhage": ("xyzPPH01", None, "maternal"),
    "pre-eclampsia": ("xyzPreeclampsia01", None, "maternal"),
    "eclampsia": ("xyzEclampsia01", None, "maternal"),
    "sepsis during pregnancy": ("xyzPregSepsis01", None, "maternal"),
    "malaria in pregnancy": ("xyzMalariaPreg01", None, "maternal"),
    "anemia in pregnancy": ("xyzAnemiaPreg01", None, "maternal"),
    "ectopic pregnancy": ("xyzEctopic01", None, "maternal"),
    "spontaneous abortion": ("xyzAbortion01", None, "maternal"),
    "induced abortion": ("xyzInducedAbort01", None, "maternal"),
    "complications of abortion": ("xyzAbortComp01", None, "maternal"),
    
    # CHILD HEALTH
    "neonatal death": ("xyzNeoDeath01", None, "child_health"),
    "low birth weight": ("xyzLBW01", None, "child_health"),
    "prematurity": ("xyzPrematurity01", None, "child_health"),
    "birth asphyxia": ("xyzBirthAsphyxia01", None, "child_health"),
    "congenital malformations": ("xyzCongenital01", None, "child_health"),
    "neonatal jaundice": ("xyzNeoJaundice01", None, "child_health"),
    "acute respiratory infection (child)": ("xyzARIChild01", None, "child_health"),
    "pneumonia (child)": ("xyzPneumoniaChild01", None, "child_health"),
    "diarrhea (child)": ("xyzDiarrheaChild01", None, "child_health"),
    "malnutrition (child)": ("xyzMalnutrition01", None, "child_health"),
    "severe acute malnutrition": ("xyzSAM01", None, "child_health"),
    "moderate acute malnutrition": ("xyzMAM01", None, "child_health"),
    
    # INJURIES
    "road traffic accident": ("xyzRTA01", None, "injury"),
    "fracture": ("xyzFracture01", None, "injury"),
    "head injury": ("xyzHeadInjury01", None, "injury"),
    "burns": ("xyzBurns01", None, "injury"),
    "drowning": ("xyzDrowning01", None, "injury"),
    "snake bite": ("xyzSnakeBite01", None, "injury"),
    "dog bite": ("xyzDogBite01", None, "injury"),
    "assault": ("xyzAssault01", None, "injury"),
    "industrial accident": ("xyzIndustrial01", None, "injury"),
    "sports injury": ("xyzSports01", None, "injury"),
    
    # MENTAL HEALTH
    "depression": ("xyzDepression01", None, "mental_health"),
    "anxiety disorder": ("xyzAnxiety01", None, "mental_health"),
    "psychosis": ("xyzPsychosis01", None, "mental_health"),
    "schizophrenia": ("xyzSchizophrenia01", None, "mental_health"),
    "bipolar disorder": ("xyzBipolar01", None, "mental_health"),
    "mental retardation": ("xyzMentalRetard01", None, "mental_health"),
    "alcohol abuse": ("xyzAlcohol01", None, "mental_health"),
    "drug abuse": ("xyzDrugAbuse01", None, "mental_health"),
    "suicide": ("xyzSuicide01", None, "mental_health"),
    
    # EYE CONDITIONS
    "cataract": ("xyzCataract01", None, "eye_conditions"),
    "glaucoma": ("xyzGlaucoma01", None, "eye_conditions"),
    "conjunctivitis": ("xyzConjunctivitis01", None, "eye_conditions"),
    "trachoma": ("xyzTrachoma01", None, "eye_conditions"),
    "blindness": ("xyzBlindness01", None, "eye_conditions"),
    "eye injury": ("xyzEyeInjury01", None, "eye_conditions"),
    
    # DENTAL
    "dental caries": ("xyzDentalCaries01", None, "dental"),
    "periodontal disease": ("xyzPeriodontal01", None, "dental"),
    "tooth abscess": ("xyzToothAbscess01", None, "dental"),
    "oral ulceration": ("xyzOralUlcer01", None, "dental"),
    
    # SKIN DISEASES
    "cellulitis": ("xyzCellulitis01", None, "skin"),
    "skin ulcer": ("xyzSkinUlcer01", None, "skin"),
    "scabies": ("xyzScabies01", None, "skin"),
    "ringworm": ("xyzRingworm01", None, "skin"),
    "impetigo": ("xyzImpetigo01", None, "skin"),
    "herpes zoster": ("xyzHerpesZoster01", None, "skin"),
    "eczema": ("xyzEczema01", None, "skin"),
    "psoriasis": ("xyzPsoriasis01", None, "skin"),
    
    # RESPIRATORY
    "acute respiratory infection": ("xyzARI01", None, "respiratory"),
    "pneumonia": ("xyzPneumonia01", None, "respiratory"),
    "bronchitis": ("xyzBronchitis01", None, "respiratory"),
    "bronchiolitis": ("xyzBronchiolitis01", None, "respiratory"),
    "pneumothorax": ("xyzPneumothorax01", None, "respiratory"),
    "pleural effusion": ("xyzPleuralEff01", None, "respiratory"),
    "lung abscess": ("xyzLungAbscess01", None, "respiratory"),
}


def get_category_enum(category_name):
    """Convert category string to enum value"""
    category_map = {
        "infectious": "infectious",
        "ncd": "ncd",
        "maternal": "maternal",
        "child_health": "child_health",
        "injury": "injury",
        "mental_health": "mental_health",
        "eye_conditions": "eye_conditions",
        "dental": "dental",
        "skin": "skin",
        "respiratory": "respiratory",
        "other": "other"
    }
    return category_map.get(category_name.lower(), "other")


def update_disease_mappings():
    """Update diseases with DHIS2 mappings"""
    print("=" * 60)
    print("Updating Disease DHIS2 Mappings")
    print("=" * 60)
    
    updated_count = 0
    not_found = []
    
    for disease_name, (dhis2_uid, combo_uid, category) in DHIS2_MAPPINGS.items():
        try:
            # Try to find disease by name (case-insensitive)
            cursor.execute(
                "SELECT id, name FROM diseases WHERE LOWER(name) = %s",
                (disease_name.lower(),)
            )
            result = cursor.fetchone()
            
            if result:
                disease_id, current_name = result
                
                # Update the disease with DHIS2 mapping
                cursor.execute(
                    """
                    UPDATE diseases 
                    SET dhis2_data_element_uid = %s,
                        dhis2_category_option_combo_uid = %s,
                        category = %s::diseasecategory
                    WHERE id = %s
                    """,
                    (dhis2_uid, combo_uid, get_category_enum(category), disease_id)
                )
                print(f"✓ Updated: {current_name} -> {dhis2_uid}")
                updated_count += 1
            else:
                not_found.append(disease_name)
                
        except Exception as e:
            print(f"✗ Error updating {disease_name}: {e}")
    
    conn.commit()
    
    print(f"\n{'=' * 60}")
    print(f"Summary:")
    print(f"  - Diseases updated: {updated_count}")
    print(f"  - Diseases not found: {len(not_found)}")
    if not_found:
        print(f"\nNot found diseases ({len(not_found)}):")
        for name in not_found[:20]:  # Show first 20
            print(f"  - {name}")
        if len(not_found) > 20:
            print(f"  ... and {len(not_found) - 20} more")
    print(f"{'=' * 60}")
    
    return updated_count, not_found


def show_mapping_stats():
    """Show current mapping statistics"""
    print("\nCurrent Mapping Statistics:")
    print("-" * 40)
    
    # Total diseases
    cursor.execute("SELECT COUNT(*) FROM diseases")
    total = cursor.fetchone()[0]
    print(f"Total diseases: {total}")
    
    # Mapped diseases
    cursor.execute(
        "SELECT COUNT(*) FROM diseases WHERE dhis2_data_element_uid IS NOT NULL"
    )
    mapped = cursor.fetchone()[0]
    print(f"Diseases with DHIS2 mapping: {mapped}")
    print(f"Diseases without mapping: {total - mapped}")
    
    # By category
    print("\nBy Category:")
    cursor.execute("""
        SELECT category, COUNT(*) as count,
               COUNT(dhis2_data_element_uid) as mapped
        FROM diseases 
        GROUP BY category
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        cat, total_cat, mapped_cat = row
        print(f"  {cat}: {mapped_cat}/{total_cat} mapped")


if __name__ == "__main__":
    try:
        update_disease_mappings()
        show_mapping_stats()
        print("\n✓ DHIS2 mapping update completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
