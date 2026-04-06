"""
Seed script to update Diseases (ICD) based on GHS and DHIMS standards.

This script populates the diseases table with comprehensive ICD-10 codes
aligned with Ghana Health Service (GHS) and DHIMS2 reporting requirements.

Uses raw SQL to handle PostgreSQL enum types properly.
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

# Connect to database - use postgresql:// for psycopg2 (not postgresql+psycopg2)
db_url_for_psycopg2 = db_url.replace('postgresql+psycopg2://', 'postgresql://')
conn = psycopg2.connect(db_url_for_psycopg2)
conn.autocommit = False
cursor = conn.cursor()

# Comprehensive disease list with ICD-10 codes and categories
# Based on GHS and DHIMS2 reporting requirements for Ghana
diseases_data = [
    # ========================================================================
    # INFECTIOUS DISEASES (Notifiable Diseases)
    # ========================================================================
    {"name": "Cholera", "code": "A00", "category": "infectious"},
    {"name": "Unspecified Cholera", "code": "A00.9", "category": "infectious"},
    {"name": "Typhoid Fever", "code": "A01.0", "category": "infectious"},
    {"name": "Amoebiasis", "code": "A06", "category": "infectious"},
    {"name": "Shigellosis", "code": "A03", "category": "infectious"},
    {"name": "Diarrhea without dehydration", "code": "K52.9", "category": "infectious"},
    {"name": "Diarrhea with moderate dehydration", "code": "K52.9", "category": "infectious"},
    {"name": "Diarrhea with severe dehydration", "code": "K52.9", "category": "infectious"},
    
    # Viral Diseases
    {"name": "Measles", "code": "B05", "category": "infectious"},
    {"name": "Rubella", "code": "B06", "category": "infectious"},
    {"name": "Yellow Fever", "code": "A95", "category": "infectious"},
    {"name": "Viral Hepatitis A", "code": "B15", "category": "infectious"},
    {"name": "Viral Hepatitis B", "code": "B16", "category": "infectious"},
    {"name": "Viral Hepatitis C", "code": "B17.1", "category": "infectious"},
    {"name": "Viral Hepatitis E", "code": "B17.2", "category": "infectious"},
    {"name": "HIV/AIDS", "code": "B20-B24", "category": "infectious"},
    {"name": "Human Immunodeficiency Virus (HIV)", "code": "B20", "category": "infectious"},
    {"name": "COVID-19", "code": "U07.1", "category": "infectious"},
    
    # Influenza
    {"name": "Influenza", "code": "J11", "category": "infectious"},
    {"name": "Influenza with pneumonia", "code": "J10.0", "category": "infectious"},
    {"name": "Influenza with other respiratory manifestations", "code": "J10.1", "category": "infectious"},
    
    # Vector-borne Diseases
    {"name": "Malaria (Uncomplicated)", "code": "B50", "category": "infectious"},
    {"name": "Severe Malaria", "code": "B50.0", "category": "infectious"},
    {"name": "Malaria with cerebral complications", "code": "B50.0", "category": "infectious"},
    {"name": "Malaria with severe anemia", "code": "B50.0", "category": "infectious"},
    {"name": "Onchocerciasis", "code": "B73", "category": "infectious"},
    {"name": "Schistosomiasis", "code": "B65", "category": "infectious"},
    {"name": "Lymphatic filariasis", "code": "B74", "category": "infectious"},
    {"name": "Dengue fever", "code": "A90", "category": "infectious"},
    {"name": "Chikungunya", "code": "A92.0", "category": "infectious"},
    
    # Tuberculosis
    {"name": "Pulmonary Tuberculosis (New)", "code": "A15.0", "category": "infectious"},
    {"name": "Pulmonary Tuberculosis (Relapse)", "code": "A15.0", "category": "infectious"},
    {"name": "Extra-pulmonary Tuberculosis", "code": "A17", "category": "infectious"},
    {"name": "Tuberculous meningitis", "code": "A17.0", "category": "infectious"},
    {"name": "Tuberculosis of lymph nodes", "code": "A18.2", "category": "infectious"},
    {"name": "Tuberculosis of bones and joints", "code": "A18.0", "category": "infectious"},
    {"name": "Miliary Tuberculosis", "code": "A19", "category": "infectious"},
    {"name": "Drug-resistant TB (DR-TB)", "code": "U84.2", "category": "infectious"},
    
    # Bacterial Infections
    {"name": "Meningitis (Bacterial)", "code": "G00", "category": "infectious"},
    {"name": "Meningococcal Meningitis", "code": "A39.0", "category": "infectious"},
    {"name": "Pneumococcal Meningitis", "code": "G00.1", "category": "infectious"},
    {"name": "Meningitis (unspecified)", "code": "G03.9", "category": "infectious"},
    {"name": "Sepsis", "code": "A41", "category": "infectious"},
    {"name": "Neonatal Sepsis", "code": "P36", "category": "infectious"},
    {"name": "Tetanus", "code": "A35", "category": "infectious"},
    {"name": "Neonatal Tetanus", "code": "A33", "category": "infectious"},
    {"name": "Diphtheria", "code": "A36", "category": "infectious"},
    {"name": "Whooping Cough (Pertussis)", "code": "A37", "category": "infectious"},
    {"name": "Acute Poliomyelitis", "code": "A80", "category": "infectious"},
    {"name": "Leprosy", "code": "A30", "category": "infectious"},
    {"name": "Buruli Ulcer", "code": "A92.3", "category": "infectious"},
    
    # Viral Infections
    {"name": "Rabies", "code": "A82", "category": "infectious"},
    {"name": "Chickenpox", "code": "B01", "category": "infectious"},
    {"name": "Mumps", "code": "B26", "category": "infectious"},
    {"name": "Herpes zoster", "code": "B02", "category": "infectious"},
    {"name": "Herpes simplex", "code": "B00", "category": "infectious"},
    
    # Other Infectious
    {"name": "Helminthiasis", "code": "B82", "category": "infectious"},
    {"name": "Intestinal worms", "code": "B79", "category": "infectious"},
    {"name": "Skin infection", "code": "L08.9", "category": "infectious"},
    {"name": "Urinary Tract Infection", "code": "N39.0", "category": "infectious"},
    {"name": "Other Infectious Diseases", "code": "B99", "category": "infectious"},
    
    # ========================================================================
    # NON-COMMUNICABLE DISEASES (NCDs)
    # ========================================================================
    
    # Diabetes
    {"name": "Type 1 Diabetes Mellitus", "code": "E10", "category": "ncd"},
    {"name": "Type 2 Diabetes Mellitus", "code": "E11", "category": "ncd"},
    {"name": "Diabetes Mellitus (unspecified)", "code": "E14", "category": "ncd"},
    {"name": "Diabetes with ketoacidosis", "code": "E10.1", "category": "ncd"},
    {"name": "Diabetes with nephropathy", "code": "E10.2", "category": "ncd"},
    {"name": "Diabetes with retinopathy", "code": "E10.3", "category": "ncd"},
    {"name": "Diabetes with peripheral circulatory disease", "code": "E10.5", "category": "ncd"},
    
    # Hypertension
    {"name": "Essential Hypertension", "code": "I10", "category": "ncd"},
    {"name": "Hypertensive heart disease", "code": "I11", "category": "ncd"},
    {"name": "Hypertensive renal disease", "code": "I12", "category": "ncd"},
    {"name": "Hypertensive heart and renal disease", "code": "I13", "category": "ncd"},
    {"name": "Secondary Hypertension", "code": "I15", "category": "ncd"},
    {"name": "Malignant Hypertension", "code": "I10.0", "category": "ncd"},
    
    # Heart Diseases
    {"name": "Acute Myocardial Infarction", "code": "I21", "category": "ncd"},
    {"name": "Angina Pectoris", "code": "I20", "category": "ncd"},
    {"name": "Unstable Angina", "code": "I20.0", "category": "ncd"},
    {"name": "Chronic Ischemic Heart Disease", "code": "I25", "category": "ncd"},
    {"name": "Heart Failure", "code": "I50", "category": "ncd"},
    {"name": "Congestive Heart Failure", "code": "I50.0", "category": "ncd"},
    {"name": "Left ventricular failure", "code": "I50.1", "category": "ncd"},
    {"name": "Cardiomyopathy", "code": "I42", "category": "ncd"},
    {"name": "Arrhythmia", "code": "I49", "category": "ncd"},
    {"name": "Atrial fibrillation", "code": "I48", "category": "ncd"},
    {"name": "Valvular heart disease", "code": "I35", "category": "ncd"},
    {"name": "Rheumatic heart disease", "code": "I05", "category": "ncd"},
    
    # Cerebrovascular Diseases
    {"name": "Cerebral Infarction", "code": "I63", "category": "ncd"},
    {"name": "Intracerebral hemorrhage", "code": "I61", "category": "ncd"},
    {"name": "Subarachnoid hemorrhage", "code": "I60", "category": "ncd"},
    {"name": "Cerebrovascular disease (unspecified)", "code": "I64", "category": "ncd"},
    {"name": "Sequelae of cerebrovascular disease", "code": "I69", "category": "ncd"},
    
    # Respiratory Diseases
    {"name": "Asthma", "code": "J45", "category": "respiratory"},
    {"name": "Asthma with acute exacerbation", "code": "J45.0", "category": "respiratory"},
    {"name": "Chronic Obstructive Pulmonary Disease (COPD)", "code": "J44", "category": "respiratory"},
    {"name": "Emphysema", "code": "J43", "category": "respiratory"},
    {"name": "Chronic Bronchitis", "code": "J42", "category": "respiratory"},
    {"name": "Bronchiectasis", "code": "J47", "category": "respiratory"},
    {"name": "Pneumonia", "code": "J18", "category": "respiratory"},
    {"name": "Community-Acquired Pneumonia", "code": "J18.9", "category": "respiratory"},
    {"name": "Bronchopneumonia", "code": "J17", "category": "respiratory"},
    {"name": "Lobar Pneumonia", "code": "J13", "category": "respiratory"},
    {"name": "Lung Abscess", "code": "J85", "category": "respiratory"},
    {"name": "Pleural Effusion", "code": "J91", "category": "respiratory"},
    {"name": "Respiratory Failure", "code": "J96", "category": "respiratory"},
    {"name": "Acute Respiratory Distress Syndrome", "code": "J80", "category": "respiratory"},
    
    # Gastrointestinal Diseases
    {"name": "Peptic Ulcer Disease", "code": "K25", "category": "ncd"},
    {"name": "Gastric Ulcer", "code": "K25", "category": "ncd"},
    {"name": "Duodenal Ulcer", "code": "K26", "category": "ncd"},
    {"name": "Gastritis", "code": "K29", "category": "ncd"},
    {"name": "Acute Gastritis", "code": "K29.1", "category": "ncd"},
    {"name": "Chronic Gastritis", "code": "K29.5", "category": "ncd"},
    {"name": "Gastroesophageal Reflux Disease (GERD)", "code": "K21", "category": "ncd"},
    {"name": "Cirrhosis of liver", "code": "K74.6", "category": "ncd"},
    {"name": "Chronic Liver Disease", "code": "K73", "category": "ncd"},
    {"name": "Hepatic Failure", "code": "K72", "category": "ncd"},
    {"name": "Cholecystitis", "code": "K81", "category": "ncd"},
    {"name": "Gallstones", "code": "K80", "category": "ncd"},
    {"name": "Pancreatitis", "code": "K85", "category": "ncd"},
    {"name": "Acute Pancreatitis", "code": "K85", "category": "ncd"},
    {"name": "Chronic Pancreatitis", "code": "K86.1", "category": "ncd"},
    {"name": "Inflammatory Bowel Disease", "code": "K50", "category": "ncd"},
    {"name": "Ulcerative Colitis", "code": "K51", "category": "ncd"},
    {"name": "Appendicitis", "code": "K35", "category": "ncd"},
    {"name": "Intestinal obstruction", "code": "K56", "category": "ncd"},
    {"name": "Hernia", "code": "K40", "category": "ncd"},
    
    # Renal Diseases
    {"name": "Chronic Kidney Disease", "code": "N18", "category": "ncd"},
    {"name": "Renal Failure", "code": "N17", "category": "ncd"},
    {"name": "Acute Kidney Injury", "code": "N17", "category": "ncd"},
    {"name": "Nephrotic Syndrome", "code": "N04", "category": "ncd"},
    {"name": "Nephritis", "code": "N05", "category": "ncd"},
    {"name": "Renal Colic", "code": "N23", "category": "ncd"},
    {"name": "Urinary Stones", "code": "N20", "category": "ncd"},
    
    # Cancers
    {"name": "Breast Cancer", "code": "C50", "category": "ncd"},
    {"name": "Cervical Cancer", "code": "C53", "category": "ncd"},
    {"name": "Prostate Cancer", "code": "C61", "category": "ncd"},
    {"name": "Liver Cancer", "code": "C22", "category": "ncd"},
    {"name": "Lung Cancer", "code": "C34", "category": "ncd"},
    {"name": "Colon Cancer", "code": "C18", "category": "ncd"},
    {"name": "Rectal Cancer", "code": "C20", "category": "ncd"},
    {"name": "Stomach Cancer", "code": "C16", "category": "ncd"},
    {"name": "Esophageal Cancer", "code": "C15", "category": "ncd"},
    {"name": "Leukemia", "code": "C91", "category": "ncd"},
    {"name": "Lymphoma", "code": "C82", "category": "ncd"},
    {"name": "Nasopharyngeal Cancer", "code": "C11", "category": "ncd"},
    {"name": "Thyroid Cancer", "code": "C73", "category": "ncd"},
    {"name": "Skin Cancer", "code": "C44", "category": "ncd"},
    {"name": "Bladder Cancer", "code": "C67", "category": "ncd"},
    {"name": "Kidney Cancer", "code": "C64", "category": "ncd"},
    
    # Musculoskeletal
    {"name": "Rheumatoid Arthritis", "code": "M06", "category": "ncd"},
    {"name": "Osteoarthritis", "code": "M19", "category": "ncd"},
    {"name": "Gout", "code": "M10", "category": "ncd"},
    {"name": "Osteoporosis", "code": "M81", "category": "ncd"},
    {"name": "Back pain", "code": "M54", "category": "ncd"},
    {"name": "Fibromyalgia", "code": "M79.0", "category": "ncd"},
    {"name": "Arthritis (unspecified)", "code": "M13", "category": "ncd"},
    
    # Other NCDs
    {"name": "Sickle Cell Disease", "code": "D57", "category": "ncd"},
    {"name": "Sickle Cell Trait", "code": "D57.3", "category": "ncd"},
    {"name": "Anemia", "code": "D64", "category": "ncd"},
    {"name": "Iron deficiency anemia", "code": "D50", "category": "ncd"},
    {"name": "Vitamin B12 deficiency anemia", "code": "D51", "category": "ncd"},
    {"name": "Folate deficiency anemia", "code": "D52", "category": "ncd"},
    {"name": "Aplastic anemia", "code": "D61", "category": "ncd"},
    {"name": "Thalassemia", "code": "D56", "category": "ncd"},
    
    # ========================================================================
    # MATERNAL HEALTH CONDITIONS
    # ========================================================================
    
    # Pregnancy Complications
    {"name": "Ectopic Pregnancy", "code": "O00", "category": "maternal"},
    {"name": "Hydatidiform Mole", "code": "O01", "category": "maternal"},
    {"name": "Miscarriage (Spontaneous abortion)", "code": "O03", "category": "maternal"},
    {"name": "Induced Abortion", "code": "O04", "category": "maternal"},
    {"name": "Threatened abortion", "code": "O20.0", "category": "maternal"},
    {"name": "Hyperemesis Gravidarum", "code": "O21", "category": "maternal"},
    
    # Hypertensive Disorders in Pregnancy
    {"name": "Gestational Hypertension", "code": "O13", "category": "maternal"},
    {"name": "Pre-eclampsia", "code": "O14", "category": "maternal"},
    {"name": "Mild Pre-eclampsia", "code": "O14.0", "category": "maternal"},
    {"name": "Severe Pre-eclampsia", "code": "O14.1", "category": "maternal"},
    {"name": "Eclampsia", "code": "O15", "category": "maternal"},
    
    # Hemorrhage
    {"name": "Antepartum Hemorrhage", "code": "O46", "category": "maternal"},
    {"name": "Placenta Praevia", "code": "O44", "category": "maternal"},
    {"name": "Placental Abruption", "code": "O45", "category": "maternal"},
    {"name": "Postpartum Hemorrhage", "code": "O72", "category": "maternal"},
    
    # Infections in Pregnancy
    {"name": "Urinary Tract Infection in Pregnancy", "code": "O23", "category": "maternal"},
    {"name": "Chorioamnionitis", "code": "O41.1", "category": "maternal"},
    
    # Other Maternal Conditions
    {"name": "Gestational Diabetes", "code": "O24.4", "category": "maternal"},
    {"name": "Premature Labor", "code": "O60", "category": "maternal"},
    {"name": "Premature Rupture of Membranes", "code": "O42", "category": "maternal"},
    {"name": "Obstructed Labor", "code": "O64", "category": "maternal"},
    {"name": "Uterine Rupture", "code": "O71.0", "category": "maternal"},
    {"name": "Puerperal Sepsis", "code": "O85", "category": "maternal"},
    {"name": "Mastitis", "code": "O91", "category": "maternal"},
    {"name": "Anemia in Pregnancy", "code": "O99.0", "category": "maternal"},
    
    # Delivery
    {"name": "Normal Delivery", "code": "O80", "category": "maternal"},
    {"name": "Cesarean Section", "code": "O82", "category": "maternal"},
    {"name": "Instrumental Delivery", "code": "O81", "category": "maternal"},
    {"name": "Retained Placenta", "code": "O72.0", "category": "maternal"},
    
    # Gynecological Conditions
    {"name": "Menstrual Disorders", "code": "N91", "category": "maternal"},
    {"name": "Dysmenorrhea", "code": "N94.4", "category": "maternal"},
    {"name": "Menorrhagia", "code": "N92.0", "category": "maternal"},
    {"name": "Amenorrhea", "code": "N91", "category": "maternal"},
    {"name": "Ovarian Cyst", "code": "N83", "category": "maternal"},
    {"name": "Uterine Fibroids", "code": "D25", "category": "maternal"},
    {"name": "Endometriosis", "code": "N80", "category": "maternal"},
    {"name": "Pelvic Inflammatory Disease", "code": "N73", "category": "maternal"},
    {"name": "Cervicitis", "code": "N72", "category": "maternal"},
    {"name": "Vaginitis", "code": "N76", "category": "maternal"},
    {"name": "Vaginal Discharge", "code": "N89", "category": "maternal"},
    {"name": "Infertility", "code": "N97", "category": "maternal"},
    
    # ========================================================================
    # CHILD HEALTH CONDITIONS
    # ========================================================================
    
    # Neonatal Conditions
    {"name": "Prematurity", "code": "P07", "category": "child_health"},
    {"name": "Low Birth Weight", "code": "P05", "category": "child_health"},
    {"name": "Very Low Birth Weight", "code": "P05.1", "category": "child_health"},
    {"name": "Birth Asphyxia", "code": "P21", "category": "child_health"},
    {"name": "Neonatal Jaundice", "code": "P59", "category": "child_health"},
    {"name": "Neonatal Sepsis", "code": "P36", "category": "child_health"},
    {"name": "Neonatal Tetanus", "code": "A33", "category": "child_health"},
    {"name": "Congenital Malformations", "code": "Q", "category": "child_health"},
    {"name": "Cleft Lip/Palate", "code": "Q35", "category": "child_health"},
    {"name": "Congenital Heart Disease", "code": "Q20", "category": "child_health"},
    {"name": "Neural Tube Defects", "code": "Q05", "category": "child_health"},
    {"name": "Hydrocephalus", "code": "Q03", "category": "child_health"},
    
    # Child Nutrition
    {"name": "Severe Acute Malnutrition (SAM)", "code": "E43", "category": "child_health"},
    {"name": "Moderate Acute Malnutrition (MAM)", "code": "E44.0", "category": "child_health"},
    {"name": "Marasmus", "code": "E42", "category": "child_health"},
    {"name": "Kwashiorkor", "code": "E40", "category": "child_health"},
    {"name": "Stunting", "code": "E44.1", "category": "child_health"},
    {"name": "Underweight", "code": "E44.1", "category": "child_health"},
    {"name": "Vitamin A Deficiency", "code": "E50", "category": "child_health"},
    {"name": "Iron Deficiency Anemia (Children)", "code": "D50.9", "category": "child_health"},
    
    # Childhood Infections
    {"name": "Acute Respiratory Infection (ARI)", "code": "J06", "category": "child_health"},
    {"name": "Pneumonia (Children)", "code": "J18", "category": "child_health"},
    {"name": "Diarrhea (Children)", "code": "K52.9", "category": "child_health"},
    {"name": "Meningitis (Children)", "code": "G03.9", "category": "child_health"},
    {"name": "Measles Complications", "code": "B05", "category": "child_health"},
    
    # Child Development
    {"name": "Developmental Delay", "code": "F88", "category": "child_health"},
    {"name": "Cerebral Palsy", "code": "G80", "category": "child_health"},
    {"name": "Intellectual Disability", "code": "F70", "category": "child_health"},
    
    # ========================================================================
    # MENTAL HEALTH CONDITIONS
    # ========================================================================
    
    {"name": "Schizophrenia", "code": "F20", "category": "mental_health"},
    {"name": "Bipolar Disorder", "code": "F31", "category": "mental_health"},
    {"name": "Depression", "code": "F32", "category": "mental_health"},
    {"name": "Major Depressive Disorder", "code": "F32", "category": "mental_health"},
    {"name": "Anxiety Disorder", "code": "F41", "category": "mental_health"},
    {"name": "Generalized Anxiety Disorder", "code": "F41.1", "category": "mental_health"},
    {"name": "Panic Disorder", "code": "F41.0", "category": "mental_health"},
    {"name": "Post-Traumatic Stress Disorder (PTSD)", "code": "F43.1", "category": "mental_health"},
    {"name": "Obsessive-Compulsive Disorder", "code": "F42", "category": "mental_health"},
    {"name": "Phobic Anxiety Disorder", "code": "F40", "category": "mental_health"},
    {"name": "Acute Stress Reaction", "code": "F43.0", "category": "mental_health"},
    {"name": "Adjustment Disorder", "code": "F43.2", "category": "mental_health"},
    
    # Substance Use Disorders
    {"name": "Alcohol Use Disorder", "code": "F10", "category": "mental_health"},
    {"name": "Alcohol Intoxication", "code": "F10.0", "category": "mental_health"},
    {"name": "Alcohol Dependence", "code": "F10.2", "category": "mental_health"},
    {"name": "Cannabis Use Disorder", "code": "F12", "category": "mental_health"},
    {"name": "Opioid Use Disorder", "code": "F11", "category": "mental_health"},
    {"name": "Cocaine Use Disorder", "code": "F14", "category": "mental_health"},
    {"name": "Tobacco Use Disorder", "code": "F17", "category": "mental_health"},
    
    # Other Mental Health
    {"name": "Dementia", "code": "F03", "category": "mental_health"},
    {"name": "Alzheimer's Disease", "code": "G30", "category": "mental_health"},
    {"name": "Delirium", "code": "F05", "category": "mental_health"},
    {"name": "Mental Retardation", "code": "F70", "category": "mental_health"},
    {"name": "Intellectual Disability", "code": "F70", "category": "mental_health"},
    {"name": "Autism Spectrum Disorder", "code": "F84", "category": "mental_health"},
    {"name": "Attention Deficit Hyperactivity Disorder (ADHD)", "code": "F90", "category": "mental_health"},
    {"name": "Conduct Disorder", "code": "F91", "category": "mental_health"},
    {"name": "Epilepsy", "code": "G40", "category": "mental_health"},
    {"name": "Epilepsy with seizures", "code": "G40", "category": "mental_health"},
    {"name": "Somatoform Disorder", "code": "F45", "category": "mental_health"},
    {"name": "Sleep Disorder", "code": "G47", "category": "mental_health"},
    {"name": "Insomnia", "code": "G47.0", "category": "mental_health"},
    {"name": "Eating Disorder", "code": "F50", "category": "mental_health"},
    
    # ========================================================================
    # INJURIES AND TRAUMA
    # ========================================================================
    
    # Road Traffic Injuries
    {"name": "Road Traffic Accident - Minor", "code": "S00", "category": "injury"},
    {"name": "Road Traffic Accident - Moderate", "code": "S00", "category": "injury"},
    {"name": "Road Traffic Accident - Severe", "code": "S00", "category": "injury"},
    {"name": "Head Injury", "code": "S06", "category": "injury"},
    {"name": "Spinal Cord Injury", "code": "S14", "category": "injury"},
    {"name": "Fracture", "code": "S82", "category": "injury"},
    {"name": "Fracture of femur", "code": "S72", "category": "injury"},
    {"name": "Fracture of tibia/fibula", "code": "S82", "category": "injury"},
    {"name": "Fracture of radius/ulna", "code": "S52", "category": "injury"},
    {"name": "Fracture of skull", "code": "S02", "category": "injury"},
    
    # Burns
    {"name": "Burns", "code": "T30", "category": "injury"},
    {"name": "Thermal Burns", "code": "T20", "category": "injury"},
    {"name": "Chemical Burns", "code": "T26", "category": "injury"},
    {"name": "Electrical Burns", "code": "T27", "category": "injury"},
    
    # Other Injuries
    {"name": "Wounds", "code": "T14", "category": "injury"},
    {"name": "Lacerations", "code": "T14.1", "category": "injury"},
    {"name": "Sprains and Strains", "code": "S93", "category": "injury"},
    {"name": "Dislocation", "code": "S03", "category": "injury"},
    {"name": "Contusion", "code": "S00", "category": "injury"},
    {"name": "Animal Bites", "code": "T14.1", "category": "injury"},
    {"name": "Snake Bite", "code": "T63.0", "category": "injury"},
    
    # Poisoning
    {"name": "Poisoning", "code": "T65", "category": "injury"},
    {"name": "Food Poisoning", "code": "A05", "category": "injury"},
    {"name": "Drug Poisoning", "code": "T50.9", "category": "injury"},
    {"name": "Pesticide Poisoning", "code": "T60", "category": "injury"},
    
    # Intentional Injuries
    {"name": "Assault", "code": "Y04", "category": "injury"},
    {"name": "Self-Harm", "code": "X60", "category": "injury"},
    {"name": "Intentional Self-Poisoning", "code": "X60", "category": "injury"},
    
    # ========================================================================
    # EYE CONDITIONS
    # ========================================================================
    
    {"name": "Cataract", "code": "H25", "category": "eye_conditions"},
    {"name": "Age-related Cataract", "code": "H25", "category": "eye_conditions"},
    {"name": "Glaucoma", "code": "H40", "category": "eye_conditions"},
    {"name": "Trachoma", "code": "A71", "category": "eye_conditions"},
    {"name": "Conjunctivitis", "code": "H10", "category": "eye_conditions"},
    {"name": "Allergic Conjunctivitis", "code": "H10.2", "category": "eye_conditions"},
    {"name": "Keratitis", "code": "H16", "category": "eye_conditions"},
    {"name": "Corneal Ulcer", "code": "H16.0", "category": "eye_conditions"},
    {"name": "Uveitis", "code": "H20", "category": "eye_conditions"},
    {"name": "Retinal Detachment", "code": "H33", "category": "eye_conditions"},
    {"name": "Macular Degeneration", "code": "H35.3", "category": "eye_conditions"},
    {"name": "Diabetic Retinopathy", "code": "E11.3", "category": "eye_conditions"},
    {"name": "Hypertensive Retinopathy", "code": "H35.0", "category": "eye_conditions"},
    {"name": "Blindness", "code": "H54", "category": "eye_conditions"},
    {"name": "Low Vision", "code": "H54.4", "category": "eye_conditions"},
    {"name": "Refractive Errors", "code": "H52", "category": "eye_conditions"},
    {"name": "Strabismus", "code": "H49", "category": "eye_conditions"},
    {"name": "Blepharitis", "code": "H01", "category": "eye_conditions"},
    {"name": "Chalazion", "code": "H00.1", "category": "eye_conditions"},
    {"name": "Stye", "code": "H00.0", "category": "eye_conditions"},
    
    # ========================================================================
    # DENTAL CONDITIONS
    # ========================================================================
    
    {"name": "Dental Caries", "code": "K02", "category": "dental"},
    {"name": "Tooth Decay", "code": "K02", "category": "dental"},
    {"name": "Pulpitis", "code": "K04", "category": "dental"},
    {"name": "Periodontitis", "code": "K05", "category": "dental"},
    {"name": "Gingivitis", "code": "K05.1", "category": "dental"},
    {"name": "Acute Gingivitis", "code": "K05.0", "category": "dental"},
    {"name": "Chronic Gingivitis", "code": "K05.1", "category": "dental"},
    {"name": "Tooth Abscess", "code": "K04.7", "category": "dental"},
    {"name": "Periapical Abscess", "code": "K04.7", "category": "dental"},
    {"name": "Tooth Loss", "code": "K08.1", "category": "dental"},
    {"name": "Impacted Teeth", "code": "K01.1", "category": "dental"},
    {"name": "Malocclusion", "code": "K07", "category": "dental"},
    {"name": "Oral Candidiasis", "code": "B37.0", "category": "dental"},
    {"name": "Aphthous Ulcer", "code": "K12.0", "category": "dental"},
    {"name": "Temporomandibular Joint Disorder", "code": "K07.6", "category": "dental"},
    
    # ========================================================================
    # SKIN CONDITIONS
    # ========================================================================
    
    {"name": "Scabies", "code": "B86", "category": "skin"},
    {"name": "Impetigo", "code": "L01", "category": "skin"},
    {"name": "Cellulitis", "code": "L03", "category": "skin"},
    {"name": "Abscess", "code": "L02", "category": "skin"},
    {"name": "Boil (Furuncle)", "code": "L02.0", "category": "skin"},
    {"name": "Carbuncle", "code": "L02.0", "category": "skin"},
    {"name": "Dermatitis", "code": "L30", "category": "skin"},
    {"name": "Atopic Dermatitis", "code": "L20", "category": "skin"},
    {"name": "Contact Dermatitis", "code": "L25", "category": "skin"},
    {"name": "Seborrheic Dermatitis", "code": "L21", "category": "skin"},
    {"name": "Eczema", "code": "L30.9", "category": "skin"},
    {"name": "Psoriasis", "code": "L40", "category": "skin"},
    {"name": "Lichen Planus", "code": "L43", "category": "skin"},
    {"name": "Urticaria", "code": "L50", "category": "skin"},
    {"name": "Hives", "code": "L50", "category": "skin"},
    {"name": "Acne", "code": "L70", "category": "skin"},
    {"name": "Fungal Skin Infection", "code": "B35", "category": "skin"},
    {"name": "Ringworm (Tinea)", "code": "B35", "category": "skin"},
    {"name": "Pityriasis", "code": "L30.5", "category": "skin"},
    {"name": "Warts", "code": "B07", "category": "skin"},
    {"name": "Molluscum Contagiosum", "code": "B08.1", "category": "skin"},
    {"name": "Herpes Zoster (Shingles)", "code": "B02", "category": "skin"},
    {"name": "Leprosy Reaction", "code": "A30", "category": "skin"},
    {"name": "Skin Ulcer", "code": "L98.4", "category": "skin"},
    {"name": "Pressure Ulcer", "code": "L89", "category": "skin"},
    
    # ========================================================================
    # SEXUALLY TRANSMITTED INFECTIONS (STIs)
    # ========================================================================
    
    {"name": "Syphilis", "code": "A50-A64", "category": "infectious"},
    {"name": "Primary Syphilis", "code": "A51.0", "category": "infectious"},
    {"name": "Secondary Syphilis", "code": "A51.3", "category": "infectious"},
    {"name": "Congenital Syphilis", "code": "A50", "category": "infectious"},
    {"name": "Gonorrhea", "code": "A54", "category": "infectious"},
    {"name": "Chlamydia", "code": "A55-A56", "category": "infectious"},
    {"name": "Chlamydial urethritis", "code": "A55", "category": "infectious"},
    {"name": "Chlamydial cervicitis", "code": "A56.0", "category": "infectious"},
    {"name": "Genital Herpes", "code": "A60", "category": "infectious"},
    {"name": "Genital Warts", "code": "A63.0", "category": "infectious"},
    {"name": "Trichomoniasis", "code": "A59", "category": "infectious"},
    {"name": "Candidiasis (Genital)", "code": "B37.3", "category": "infectious"},
    {"name": "Bacterial Vaginosis", "code": "N76.0", "category": "infectious"},
    {"name": "Lymphogranuloma Venereum", "code": "A55", "category": "infectious"},
    {"name": "Chancroid", "code": "A57", "category": "infectious"},
    
    # ========================================================================
    # OTHER/UNSPECIFIED CONDITIONS
    # ========================================================================
    
    {"name": "Generalized Body Weakness", "code": "R53", "category": "other"},
    {"name": "Fever (unspecified)", "code": "R50.9", "category": "other"},
    {"name": "Headache", "code": "R51", "category": "other"},
    {"name": "Dizziness", "code": "R42", "category": "other"},
    {"name": "Fatigue", "code": "R53", "category": "other"},
    {"name": "Weight Loss", "code": "R63.4", "category": "other"},
    {"name": "Loss of Appetite", "code": "R63.0", "category": "other"},
    {"name": "Abdominal Pain", "code": "R10", "category": "other"},
    {"name": "Chest Pain", "code": "R07", "category": "other"},
    {"name": "Back Pain", "code": "M54", "category": "other"},
    {"name": "Joint Pain", "code": "M25.5", "category": "other"},
    {"name": "Swelling", "code": "R22", "category": "other"},
    {"name": "Jaundice (unspecified)", "code": "R17", "category": "other"},
    {"name": "Ascites", "code": "R18", "category": "other"},
    {"name": "Edema", "code": "R60", "category": "other"},
    {"name": "Cough", "code": "R05", "category": "other"},
    {"name": "Shortness of Breath", "code": "R06.0", "category": "other"},
    {"name": "Wheezing", "code": "R06.1", "category": "other"},
    {"name": "Hemoptysis", "code": "R04.2", "category": "other"},
    {"name": "Nausea and Vomiting", "code": "R11", "category": "other"},
    {"name": "Diarrhea", "code": "K52.9", "category": "other"},
    {"name": "Constipation", "code": "K59.0", "category": "other"},
    {"name": "Dysphagia", "code": "R13", "category": "other"},
    {"name": "Abdominal Distension", "code": "R14", "category": "other"},
    {"name": "Dysuria", "code": "R30", "category": "other"},
    {"name": "Hematuria", "code": "R31", "category": "other"},
    {"name": "Proteinuria", "code": "R80", "category": "other"},
    {"name": "Oliguria", "code": "R34", "category": "other"},
    {"name": "Rash", "code": "R21", "category": "other"},
    {"name": "Itching (Pruritus)", "code": "L29", "category": "other"},
    {"name": "Insomnia", "code": "G47.0", "category": "other"},
    {"name": "Anxiety (unspecified)", "code": "F41.9", "category": "other"},
    {"name": "Depression (unspecified)", "code": "F32.9", "category": "other"},
]


def main():
    """Main function to seed diseases"""
    print("=" * 60)
    print("Seeding Diseases (ICD) - GHS/DHIMS Standards")
    print("=" * 60)
    
    try:
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM diseases")
        existing_count = cursor.fetchone()[0]
        print(f"Current diseases in database: {existing_count}")
        
        # Fix sequence if needed
        cursor.execute("""
            SELECT setval(pg_get_serial_sequence('diseases', 'id'), 
                         COALESCE((SELECT MAX(id) FROM diseases), 1))
        """)
        
        created_count = 0
        updated_count = 0
        
        for disease_data in diseases_data:
            name = disease_data["name"]
            code = disease_data.get("code")
            category = disease_data.get("category", "other")
            description = f"ICD-10: {code}"
            
            # Check if disease exists
            cursor.execute(
                "SELECT id FROM diseases WHERE name = %s",
                (name,)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE diseases 
                    SET code = %s, 
                        description = %s, 
                        category = %s::diseasecategory,
                        is_system = true,
                        is_active = true
                    WHERE name = %s
                """, (code, description, category, name))
                updated_count += 1
            else:
                # Insert new with ON CONFLICT to handle duplicates
                cursor.execute("""
                    INSERT INTO diseases (name, code, description, category, is_system, is_active)
                    VALUES (%s, %s, %s, %s::diseasecategory, true, true)
                    ON CONFLICT (name) DO UPDATE SET
                        code = EXCLUDED.code,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        is_system = true,
                        is_active = true
                """, (name, code, description, category))
                created_count += 1
        
        conn.commit()
        
        # Get final count
        cursor.execute("SELECT COUNT(*) FROM diseases WHERE is_active = true")
        final_count = cursor.fetchone()[0]
        
        print(f"\nDisease seeding complete!")
        print(f"  - Created: {created_count}")
        print(f"  - Updated: {updated_count}")
        print(f"  - Total active diseases: {final_count}")
        
    except Exception as e:
        print(f"Error seeding diseases: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
    
    print("\nDone!")


if __name__ == "__main__":
    main()
