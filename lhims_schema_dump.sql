-- LHIMS Database Schema Dump
-- Generated on: 2026-02-07 13:39:21.103469
-- Total Tables: 55
-- Database: PostgreSQL
-- Connection: localhost:5432/lhims

-- Table: admission_notes
CREATE TABLE admission_notes (
    id integer NOT NULL DEFAULT nextval('admission_notes_id_seq'::regclass),
    admission_id integer NOT NULL,
    created_by_id integer NOT NULL,
    note text NOT NULL,
    note_type character varying(50) DEFAULT 'general'::character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true,
    parent_note_id integer
);

-- Table: admissions
CREATE TABLE admissions (
    id integer NOT NULL DEFAULT nextval('admissions_id_seq'::regclass),
    patient_id integer NOT NULL,
    encounter_id integer,
    ward_id integer NOT NULL,
    bed_id integer NOT NULL,
    admitted_by_id integer NOT NULL,
    discharged_by_id integer,
    admission_number character varying(50) NOT NULL,
    status USER-DEFINED NOT NULL DEFAULT 'admitted'::admissionstatus,
    admission_date timestamp without time zone NOT NULL DEFAULT now(),
    discharge_date timestamp without time zone,
    expected_discharge_date timestamp without time zone,
    admission_reason text,
    diagnosis text,
    notes text,
    transferred_from_ward_id integer,
    transferred_to_ward_id integer,
    transfer_reason text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true,
    invoice_id integer,
    ready_for_discharge_at timestamp without time zone,
    discharge_status USER-DEFINED,
    discharge_diagnosis text,
    discharge_notes text
);

-- Table: alembic_version
CREATE TABLE alembic_version (
    version_num character varying(32) NOT NULL
);

-- Table: antenatal_visits
CREATE TABLE antenatal_visits (
    id integer NOT NULL DEFAULT nextval('antenatal_visits_id_seq'::regclass),
    patient_id integer NOT NULL,
    encounter_id integer,
    recorded_by_id integer,
    visit_date date NOT NULL,
    visit_number integer,
    gestational_weeks numeric,
    lmp date,
    edd date,
    blood_pressure_systolic integer,
    blood_pressure_diastolic integer,
    weight_kg numeric,
    height_cm numeric,
    bmi numeric,
    fetal_heart_rate integer,
    fundal_height_cm numeric,
    fetal_position character varying(50),
    fetal_movement character varying(50),
    hemoglobin numeric,
    urine_protein character varying(20),
    blood_group character varying(10),
    rhesus_factor character varying(5),
    risk_factors text,
    complications text,
    counseling_given text,
    supplements_prescribed text,
    next_visit_date date,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: audit_logs
CREATE TABLE audit_logs (
    id integer NOT NULL DEFAULT nextval('audit_logs_id_seq'::regclass),
    user_id integer NOT NULL,
    username character varying(100),
    action USER-DEFINED NOT NULL,
    resource_type character varying(100),
    resource_id integer,
    ip_address character varying(50),
    user_agent character varying(500),
    request_method character varying(10),
    request_path character varying(500),
    old_values text,
    new_values text,
    description text,
    status character varying(50),
    error_message text,
    created_at timestamp without time zone NOT NULL DEFAULT now()
);

-- Table: bed_types
CREATE TABLE bed_types (
    id integer NOT NULL DEFAULT nextval('bed_types_id_seq'::regclass),
    name character varying(50) NOT NULL,
    code character varying(20),
    description text,
    default_charge_per_day character varying(20),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: beds
CREATE TABLE beds (
    id integer NOT NULL DEFAULT nextval('beds_id_seq'::regclass),
    ward_id integer NOT NULL,
    bed_number character varying(50) NOT NULL,
    bed_name character varying(100),
    status USER-DEFINED NOT NULL DEFAULT 'available'::bedstatus,
    bed_type character varying(50),
    charge_per_day numeric NOT NULL DEFAULT 0.00,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: birth_records
CREATE TABLE birth_records (
    id integer NOT NULL DEFAULT nextval('birth_records_id_seq'::regclass),
    mother_patient_id integer NOT NULL,
    admission_id integer,
    encounter_id integer,
    birth_date date NOT NULL,
    birth_time time without time zone,
    delivery_type character varying(20) NOT NULL DEFAULT 'vaginal'::character varying,
    birth_outcome character varying(20) NOT NULL DEFAULT 'live'::character varying,
    gender character varying(10),
    weight_kg numeric,
    length_cm numeric,
    head_circumference_cm numeric,
    apgar_1min integer,
    apgar_5min integer,
    apgar_10min integer,
    delivered_by_id integer,
    assisted_by_id integer,
    birth_number character varying(50),
    gravida integer,
    para integer,
    complications text,
    notes text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: charge_payments
CREATE TABLE charge_payments (
    id integer NOT NULL DEFAULT nextval('charge_payments_id_seq'::regclass),
    payment_id integer NOT NULL,
    charge_id integer NOT NULL,
    amount numeric NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: charges
CREATE TABLE charges (
    id integer NOT NULL DEFAULT nextval('charges_id_seq'::regclass),
    invoice_id integer NOT NULL,
    encounter_id integer,
    lab_order_id integer,
    radiology_order_id integer,
    prescription_id integer,
    charge_type USER-DEFINED NOT NULL,
    description character varying(500) NOT NULL,
    quantity integer NOT NULL,
    unit_price numeric NOT NULL,
    discount numeric NOT NULL,
    tax_rate numeric NOT NULL,
    tax_amount numeric NOT NULL,
    total_amount numeric NOT NULL,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    opd_visit_id integer,
    admission_id integer
);

-- Table: departments
CREATE TABLE departments (
    id integer NOT NULL DEFAULT nextval('departments_id_seq'::regclass),
    name character varying(100) NOT NULL,
    code character varying(20),
    description text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: diseases
CREATE TABLE diseases (
    id integer NOT NULL DEFAULT nextval('diseases_id_seq'::regclass),
    name character varying(500) NOT NULL,
    code character varying(50),
    description text,
    is_active boolean DEFAULT true,
    is_system boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    created_by_id integer
);

-- Table: doctor_duties
CREATE TABLE doctor_duties (
    id integer NOT NULL DEFAULT nextval('doctor_duties_id_seq'::regclass),
    doctor_id integer NOT NULL,
    department character varying(100) NOT NULL,
    duty_date timestamp without time zone NOT NULL,
    shift_start timestamp without time zone NOT NULL,
    shift_end timestamp without time zone NOT NULL,
    shift_type character varying(50),
    is_on_duty boolean DEFAULT true,
    status character varying(50) DEFAULT 'scheduled'::character varying,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: drug_administrations
CREATE TABLE drug_administrations (
    id integer NOT NULL DEFAULT nextval('drug_administrations_id_seq'::regclass),
    admission_id integer NOT NULL,
    prescription_id integer NOT NULL,
    administered_by_id integer NOT NULL,
    administration_time timestamp without time zone NOT NULL,
    dosage_given character varying(100),
    route character varying(50),
    notes text,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: drug_interactions
CREATE TABLE drug_interactions (
    id integer NOT NULL DEFAULT nextval('drug_interactions_id_seq'::regclass),
    medication1_id integer NOT NULL,
    medication2_id integer NOT NULL,
    interaction_type character varying(100) NOT NULL,
    severity character varying(50) NOT NULL,
    description text NOT NULL,
    clinical_significance text,
    management text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: encounter_diseases
CREATE TABLE encounter_diseases (
    id integer NOT NULL DEFAULT nextval('encounter_diseases_id_seq'::regclass),
    encounter_id integer NOT NULL,
    disease_id integer NOT NULL,
    is_primary boolean DEFAULT false,
    custom_name character varying(500),
    created_at timestamp without time zone DEFAULT now()
);

-- Table: encounters
CREATE TABLE encounters (
    id integer NOT NULL DEFAULT nextval('encounters_id_seq'::regclass),
    patient_id integer NOT NULL,
    appointment_id integer,
    clinician_id integer NOT NULL,
    status USER-DEFINED NOT NULL,
    encounter_date timestamp without time zone NOT NULL DEFAULT now(),
    chief_complaint text,
    history_of_present_illness text,
    past_medical_history text,
    allergies text,
    medications text,
    physical_examination text,
    assessment text,
    plan text,
    primary_diagnosis_code character varying(20),
    primary_diagnosis_description character varying(500),
    secondary_diagnosis_codes text,
    started_at timestamp without time zone DEFAULT now(),
    completed_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean,
    differential_diagnosis_data text,
    opd_visit_id integer,
    admission_id integer,
    queue_entry_id integer
);

-- Table: expenses
CREATE TABLE expenses (
    id integer NOT NULL DEFAULT nextval('expenses_id_seq'::regclass),
    expense_number character varying(50) NOT NULL,
    description text NOT NULL,
    category USER-DEFINED NOT NULL,
    amount numeric NOT NULL,
    currency character varying(10) NOT NULL,
    vendor_name character varying(200),
    vendor_contact character varying(100),
    invoice_number character varying(100),
    status USER-DEFINED NOT NULL,
    approved_by_id integer,
    approved_at timestamp without time zone,
    payment_method character varying(50),
    payment_date timestamp without time zone,
    payment_reference character varying(100),
    expense_date timestamp without time zone NOT NULL DEFAULT now(),
    due_date timestamp without time zone,
    notes text,
    receipt_path character varying(500),
    created_by_id integer NOT NULL,
    department character varying(100),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: fluid_balance
CREATE TABLE fluid_balance (
    id integer NOT NULL DEFAULT nextval('fluid_balance_id_seq'::regclass),
    admission_id integer NOT NULL,
    recorded_by_id integer NOT NULL,
    entry_type character varying(20) NOT NULL,
    volume_ml integer NOT NULL,
    recorded_at timestamp without time zone NOT NULL DEFAULT now(),
    notes text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: formulary_rules
CREATE TABLE formulary_rules (
    id integer NOT NULL DEFAULT nextval('formulary_rules_id_seq'::regclass),
    rule_name character varying(255) NOT NULL,
    rule_type character varying(100) NOT NULL,
    description text,
    medication_id integer,
    medication_category character varying(100),
    condition text,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: hospital_settings
CREATE TABLE hospital_settings (
    id integer NOT NULL DEFAULT nextval('hospital_settings_id_seq'::regclass),
    hospital_name character varying(255) NOT NULL DEFAULT 'Local Health Information Management System'::character varying,
    hospital_address text,
    hospital_phone character varying(50),
    hospital_email character varying(255),
    hospital_website character varying(255),
    logo_path character varying(500),
    logo_url character varying(500),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Table: image_annotations
CREATE TABLE image_annotations (
    id integer NOT NULL DEFAULT nextval('image_annotations_id_seq'::regclass),
    image_id integer NOT NULL,
    created_by_id integer NOT NULL,
    annotation_type character varying(50) NOT NULL,
    annotation_data text NOT NULL,
    measurement_value numeric,
    measurement_unit character varying(20),
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean
);

-- Table: insurance_providers
CREATE TABLE insurance_providers (
    id integer NOT NULL DEFAULT nextval('insurance_providers_id_seq'::regclass),
    name character varying(200) NOT NULL,
    code character varying(50),
    contact_person character varying(100),
    phone_number character varying(50),
    email character varying(100),
    address text,
    co_pay_rate character varying(20),
    billing_email character varying(100),
    billing_address text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: inventory_transactions
CREATE TABLE inventory_transactions (
    id integer NOT NULL DEFAULT nextval('inventory_transactions_id_seq'::regclass),
    medication_id integer NOT NULL,
    stock_item_id integer,
    prescription_id integer,
    performed_by_id integer NOT NULL,
    transaction_type USER-DEFINED NOT NULL,
    quantity integer NOT NULL,
    unit_cost numeric,
    total_cost numeric,
    reference_number character varying(100),
    notes text,
    transaction_date timestamp without time zone NOT NULL DEFAULT now(),
    created_at timestamp without time zone DEFAULT now()
);

-- Table: invoices
CREATE TABLE invoices (
    id integer NOT NULL DEFAULT nextval('invoices_id_seq'::regclass),
    patient_id integer NOT NULL,
    encounter_id integer,
    appointment_id integer,
    created_by_id integer NOT NULL,
    invoice_number character varying(50) NOT NULL,
    status USER-DEFINED NOT NULL,
    subtotal numeric NOT NULL,
    discount_amount numeric NOT NULL,
    tax_amount numeric NOT NULL,
    total_amount numeric NOT NULL,
    paid_amount numeric NOT NULL,
    balance numeric NOT NULL,
    payment_mechanism USER-DEFINED,
    nhis_number character varying(50),
    insurance_provider character varying(100),
    insurance_policy_number character varying(100),
    invoice_date timestamp without time zone NOT NULL DEFAULT now(),
    due_date timestamp without time zone,
    paid_date timestamp without time zone,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean,
    opd_visit_id integer,
    admission_id integer
);

-- Table: lab_orders
CREATE TABLE lab_orders (
    id integer NOT NULL DEFAULT nextval('lab_orders_id_seq'::regclass),
    encounter_id integer,
    ordered_by_id integer NOT NULL,
    test_name character varying(200) NOT NULL,
    test_code character varying(50),
    instructions text,
    priority character varying(20),
    status USER-DEFINED NOT NULL,
    ordered_at timestamp without time zone DEFAULT now(),
    completed_at timestamp without time zone,
    result text,
    result_entered_by_id integer,
    result_entered_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    patient_id integer,
    is_walk_in boolean DEFAULT false,
    checked_in_at timestamp without time zone,
    checked_in_by_id integer,
    opd_visit_id integer,
    admission_id integer
);

-- Table: lab_samples
CREATE TABLE lab_samples (
    id integer NOT NULL DEFAULT nextval('lab_samples_id_seq'::regclass),
    lab_order_id integer NOT NULL,
    collected_by_id integer,
    received_by_id integer,
    barcode character varying(100) NOT NULL,
    barcode_type character varying(50),
    sample_type character varying(100),
    collection_method character varying(100),
    collection_site character varying(100),
    status USER-DEFINED NOT NULL,
    collected_at timestamp without time zone,
    received_at timestamp without time zone,
    processing_started_at timestamp without time zone,
    completed_at timestamp without time zone,
    storage_location character varying(100),
    storage_temperature character varying(50),
    notes text,
    rejection_reason text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean
);

-- Table: lab_tests
CREATE TABLE lab_tests (
    id integer NOT NULL DEFAULT nextval('lab_tests_id_seq'::regclass),
    test_name character varying(255) NOT NULL,
    test_code character varying(50),
    test_category character varying(100),
    test_type character varying(100),
    description text,
    specimen_type character varying(100),
    specimen_volume character varying(50),
    collection_method character varying(200),
    storage_requirements character varying(200),
    routine_tat integer,
    urgent_tat integer,
    stat_tat integer,
    cost numeric,
    nhis_covered boolean,
    nhis_code character varying(50),
    is_active boolean,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_specialized boolean DEFAULT false
);

-- Table: medications
CREATE TABLE medications (
    id integer NOT NULL DEFAULT nextval('medications_id_seq'::regclass),
    name character varying(255) NOT NULL,
    generic_name character varying(255),
    brand_name character varying(255),
    medication_code character varying(50),
    dosage_form character varying(100),
    strength character varying(100),
    unit character varying(50),
    is_nhis_covered boolean,
    nhis_code character varying(50),
    is_formulary boolean,
    unit_cost numeric,
    unit_price numeric,
    reorder_level integer,
    reorder_quantity integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean,
    is_controlled boolean DEFAULT false
);

-- Table: nhis_claims
CREATE TABLE nhis_claims (
    id integer NOT NULL DEFAULT nextval('nhis_claims_id_seq'::regclass),
    encounter_id integer NOT NULL,
    patient_id integer NOT NULL,
    invoice_id integer,
    created_by_id integer NOT NULL,
    claim_number character varying(50) NOT NULL,
    nhis_number character varying(50) NOT NULL,
    facility_code character varying(50),
    claim_date timestamp without time zone NOT NULL DEFAULT now(),
    status USER-DEFINED NOT NULL,
    claim_data text,
    diagnosis_codes text,
    service_codes text,
    total_amount numeric NOT NULL,
    nhis_amount numeric NOT NULL,
    co_pay_amount numeric NOT NULL,
    submitted_at timestamp without time zone,
    submission_reference character varying(100),
    response_data text,
    processed_at timestamp without time zone,
    approved_amount numeric,
    rejection_reason text,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean
);

-- Table: opd_queue
CREATE TABLE opd_queue (
    id integer NOT NULL DEFAULT nextval('opd_queue_id_seq'::regclass),
    patient_id integer NOT NULL,
    department character varying(100) NOT NULL,
    department_type character varying(20) DEFAULT 'opd'::character varying,
    assigned_clinician_id integer,
    created_by_id integer NOT NULL,
    visit_type character varying(20) DEFAULT 'walk_in'::character varying,
    status character varying(20) DEFAULT 'waiting'::character varying,
    priority integer DEFAULT 5,
    queue_number integer,
    checked_in_at timestamp without time zone,
    started_at timestamp without time zone,
    completed_at timestamp without time zone,
    chief_complaint character varying(500),
    notes character varying(1000),
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: opd_visits
CREATE TABLE opd_visits (
    id integer NOT NULL DEFAULT nextval('opd_visits_id_seq'::regclass),
    patient_id integer NOT NULL,
    opd_number character varying(50) NOT NULL,
    visit_date timestamp without time zone NOT NULL DEFAULT now(),
    status USER-DEFINED NOT NULL DEFAULT 'active'::opdvisitstatus,
    payment_status character varying(20) NOT NULL DEFAULT 'pending'::character varying,
    consultation_charge_created boolean DEFAULT false,
    total_charges numeric NOT NULL DEFAULT 0.00,
    visit_type character varying(50),
    chief_complaint text,
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    completed_at timestamp without time zone,
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true,
    queue_entry_id integer,
    appointment_id integer,
    completion_outcome character varying(20)
);

-- Table: password_reset_tokens
CREATE TABLE password_reset_tokens (
    id integer NOT NULL DEFAULT nextval('password_reset_tokens_id_seq'::regclass),
    user_id integer NOT NULL,
    token character varying(255) NOT NULL,
    token_type character varying(20) NOT NULL,
    phone_number character varying(20),
    email character varying(255),
    otp_code character varying(6),
    expires_at timestamp without time zone NOT NULL,
    used boolean NOT NULL DEFAULT false,
    created_at timestamp without time zone NOT NULL DEFAULT now()
);

-- Table: patients
CREATE TABLE patients (
    id integer NOT NULL DEFAULT nextval('patients_id_seq'::regclass),
    first_name character varying NOT NULL,
    last_name character varying NOT NULL,
    gender character varying NOT NULL,
    address character varying,
    date_of_birth date NOT NULL,
    national_id character varying,
    phone_number character varying,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean,
    payment_mechanism USER-DEFINED,
    nhis_number character varying,
    insurance_provider character varying,
    insurance_policy_number character varying,
    patient_number character varying,
    languages_spoken character varying
);

-- Table: payments
CREATE TABLE payments (
    id integer NOT NULL DEFAULT nextval('payments_id_seq'::regclass),
    invoice_id integer NOT NULL,
    patient_id integer NOT NULL,
    received_by_id integer NOT NULL,
    payment_number character varying(50) NOT NULL,
    amount numeric NOT NULL,
    payment_method USER-DEFINED NOT NULL,
    status USER-DEFINED NOT NULL,
    transaction_reference character varying(100),
    receipt_number character varying(50),
    notes text,
    payment_date timestamp without time zone NOT NULL DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean
);

-- Table: permissions
CREATE TABLE permissions (
    id integer NOT NULL DEFAULT nextval('permissions_id_seq'::regclass),
    name character varying(100) NOT NULL,
    description character varying(255),
    module character varying(50),
    is_active boolean NOT NULL DEFAULT true
);

-- Table: prescriptions
CREATE TABLE prescriptions (
    id integer NOT NULL DEFAULT nextval('prescriptions_id_seq'::regclass),
    encounter_id integer NOT NULL,
    prescribed_by_id integer NOT NULL,
    medication_name character varying(200) NOT NULL,
    medication_code character varying(50),
    dosage character varying(100) NOT NULL,
    frequency character varying(100) NOT NULL,
    duration character varying(100) NOT NULL,
    quantity integer,
    instructions text,
    status USER-DEFINED NOT NULL,
    prescribed_at timestamp without time zone DEFAULT now(),
    dispensed_at timestamp without time zone,
    dispensed_by_id integer,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    medication_id integer,
    is_walk_in boolean,
    checked_in_at timestamp without time zone,
    checked_in_by_id integer,
    opd_visit_id integer,
    admission_id integer
);

-- Table: procedure_catalog
CREATE TABLE procedure_catalog (
    id integer NOT NULL DEFAULT nextval('procedure_catalog_id_seq'::regclass),
    procedure_name character varying(255) NOT NULL,
    procedure_code character varying(50),
    procedure_category character varying(100),
    procedure_type character varying(100),
    description text,
    indication text,
    preparation_instructions text,
    post_procedure_care text,
    estimated_duration_minutes integer,
    typical_duration_minutes integer,
    cash_price numeric,
    cash_currency character varying(10),
    nhis_covered boolean,
    nhis_code character varying(50),
    nhis_price numeric,
    private_insurance_covered boolean,
    private_insurance_price numeric,
    requires_anesthesia boolean,
    typical_anesthesia_type character varying(100),
    requires_operating_room boolean,
    typical_location character varying(200),
    is_specialized boolean,
    requires_consultation boolean,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    created_by_id integer,
    updated_by_id integer
);

-- Table: procedures
CREATE TABLE procedures (
    id integer NOT NULL DEFAULT nextval('procedures_id_seq'::regclass),
    patient_id integer NOT NULL,
    encounter_id integer,
    performed_by_id integer,
    ordered_by_id integer NOT NULL,
    procedure_number character varying(50) NOT NULL,
    procedure_name character varying(200) NOT NULL,
    procedure_code character varying(50),
    procedure_type USER-DEFINED NOT NULL,
    description text,
    status USER-DEFINED NOT NULL,
    scheduled_date timestamp without time zone,
    start_time timestamp without time zone,
    end_time timestamp without time zone,
    duration_minutes integer,
    indication text,
    findings text,
    complications text,
    outcome text,
    notes text,
    anesthesia_type character varying(100),
    anesthesia_provider character varying(200),
    location character varying(200),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true,
    is_walk_in boolean DEFAULT false,
    checked_in_at timestamp without time zone,
    checked_in_by_id integer,
    procedure_catalog_id integer
);

-- Table: qc_records
CREATE TABLE qc_records (
    id integer NOT NULL DEFAULT nextval('qc_records_id_seq'::regclass),
    lab_order_id integer,
    sample_id integer,
    performed_by_id integer NOT NULL,
    qc_type character varying(100) NOT NULL,
    qc_test_name character varying(255) NOT NULL,
    equipment_name character varying(255),
    reagent_lot character varying(100),
    status USER-DEFINED NOT NULL,
    expected_value numeric,
    actual_value numeric,
    deviation numeric,
    deviation_percentage numeric,
    lower_limit numeric,
    upper_limit numeric,
    notes text,
    corrective_action text,
    performed_at timestamp without time zone NOT NULL DEFAULT now(),
    expiry_date timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean
);

-- Table: radiology_images
CREATE TABLE radiology_images (
    id integer NOT NULL DEFAULT nextval('radiology_images_id_seq'::regclass),
    radiology_order_id integer NOT NULL,
    patient_id integer NOT NULL,
    uploaded_by_id integer NOT NULL,
    image_number character varying(50) NOT NULL,
    image_type USER-DEFINED NOT NULL,
    dicom_series_uid character varying(100),
    dicom_study_uid character varying(100),
    dicom_instance_uid character varying(100),
    file_path character varying(500) NOT NULL,
    file_name character varying(255) NOT NULL,
    file_size integer,
    file_format character varying(50),
    mime_type character varying(100),
    modality character varying(20),
    body_part character varying(100),
    study_description character varying(500),
    series_description character varying(500),
    image_width integer,
    image_height integer,
    bits_per_pixel integer,
    number_of_frames integer,
    acquisition_date timestamp without time zone,
    acquisition_time character varying(20),
    status USER-DEFINED NOT NULL,
    storage_location character varying(200),
    storage_tier character varying(50),
    thumbnail_path character varying(500),
    is_public boolean,
    access_level character varying(50),
    notes text,
    uploaded_at timestamp without time zone NOT NULL DEFAULT now(),
    processed_at timestamp without time zone,
    archived_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean
);

-- Table: radiology_orders
CREATE TABLE radiology_orders (
    id integer NOT NULL DEFAULT nextval('radiology_orders_id_seq'::regclass),
    encounter_id integer,
    ordered_by_id integer NOT NULL,
    study_type character varying(200) NOT NULL,
    study_code character varying(50),
    body_part character varying(100),
    clinical_indication text,
    instructions text,
    priority character varying(20),
    status USER-DEFINED NOT NULL,
    ordered_at timestamp without time zone DEFAULT now(),
    completed_at timestamp without time zone,
    report text,
    report_entered_by_id integer,
    report_entered_at timestamp without time zone,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    patient_id integer,
    is_walk_in boolean DEFAULT false,
    checked_in_at timestamp without time zone,
    checked_in_by_id integer,
    opd_visit_id integer,
    admission_id integer
);

-- Table: receipts
CREATE TABLE receipts (
    id integer NOT NULL DEFAULT nextval('receipts_id_seq'::regclass),
    payment_id integer NOT NULL,
    patient_id integer NOT NULL,
    invoice_id integer NOT NULL,
    generated_by_id integer NOT NULL,
    receipt_number character varying(50) NOT NULL,
    amount numeric NOT NULL,
    payment_method character varying(50) NOT NULL,
    currency character varying(10) NOT NULL DEFAULT 'GHS'::character varying,
    generated_at timestamp without time zone NOT NULL DEFAULT now(),
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

-- Table: reference_ranges
CREATE TABLE reference_ranges (
    id integer NOT NULL DEFAULT nextval('reference_ranges_id_seq'::regclass),
    test_name character varying(255) NOT NULL,
    test_code character varying(50),
    age_min integer,
    age_max integer,
    gender character varying(20),
    normal_min numeric,
    normal_max numeric,
    critical_low numeric,
    critical_high numeric,
    unit character varying(50),
    notes text,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean,
    test_id integer
);

-- Table: role_permissions
CREATE TABLE role_permissions (
    role_id integer NOT NULL,
    permission_id integer NOT NULL
);

-- Table: roles
CREATE TABLE roles (
    id integer NOT NULL DEFAULT nextval('roles_id_seq'::regclass),
    name character varying(50) NOT NULL,
    description character varying(255)
);

-- Table: scheduled_appointments
CREATE TABLE scheduled_appointments (
    id integer NOT NULL DEFAULT nextval('scheduled_appointments_id_seq'::regclass),
    patient_id integer,
    patient_name character varying(255),
    patient_phone character varying(20),
    department character varying(100),
    assigned_doctor_id integer NOT NULL,
    scheduled_date timestamp without time zone NOT NULL,
    duration_minutes integer DEFAULT 30,
    reason_complaint text,
    notes text,
    appointment_type character varying(50) DEFAULT 'consultation'::character varying,
    status character varying(20) DEFAULT 'scheduled'::character varying,
    priority integer DEFAULT 5,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    cancelled_at timestamp without time zone,
    completed_at timestamp without time zone,
    created_by_id integer NOT NULL,
    cancelled_by_id integer,
    is_active boolean DEFAULT true
);

-- Table: service_pricing
CREATE TABLE service_pricing (
    id integer NOT NULL DEFAULT nextval('service_pricing_id_seq'::regclass),
    service_name character varying(200) NOT NULL,
    service_code character varying(50),
    charge_type character varying(50) NOT NULL,
    category character varying(100),
    unit_price numeric NOT NULL,
    currency character varying(10) NOT NULL DEFAULT 'GHS'::character varying,
    description text,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    created_by_id integer,
    updated_by_id integer
);

-- Table: shift_types
CREATE TABLE shift_types (
    id integer NOT NULL DEFAULT nextval('shift_types_id_seq'::regclass),
    name character varying(50) NOT NULL,
    code character varying(20),
    description text,
    default_start_hour integer,
    default_end_hour integer,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: stock_items
CREATE TABLE stock_items (
    id integer NOT NULL DEFAULT nextval('stock_items_id_seq'::regclass),
    medication_id integer NOT NULL,
    batch_number character varying(100),
    expiry_date timestamp without time zone,
    manufacturing_date timestamp without time zone,
    quantity integer NOT NULL,
    reserved_quantity integer NOT NULL,
    available_quantity integer NOT NULL,
    status USER-DEFINED NOT NULL,
    location character varying(100),
    supplier character varying(255),
    purchase_date timestamp without time zone,
    purchase_price numeric,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean,
    supplier_id integer
);

-- Table: suppliers
CREATE TABLE suppliers (
    id integer NOT NULL DEFAULT nextval('suppliers_id_seq'::regclass),
    name character varying(255) NOT NULL,
    code character varying(50),
    contact_person character varying(255),
    email character varying(255),
    phone character varying(50),
    mobile character varying(50),
    address text,
    city character varying(100),
    country character varying(100),
    tax_id character varying(100),
    registration_number character varying(100),
    payment_terms character varying(100),
    credit_limit numeric,
    is_active boolean,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: triage_vitals
CREATE TABLE triage_vitals (
    id integer NOT NULL DEFAULT nextval('triage_vitals_id_seq'::regclass),
    patient_id integer NOT NULL,
    recorded_by_id integer NOT NULL,
    temperature double precision,
    blood_pressure character varying(50),
    recorded_at timestamp without time zone,
    systolic_bp integer,
    diastolic_bp integer,
    pulse_rate integer,
    respiratory_rate integer,
    oxygen_saturation integer,
    weight numeric,
    height numeric,
    bmi numeric,
    pain_scale integer,
    triage_level character varying(20),
    triage_category character varying(50),
    triage_assigned_by_id integer,
    triage_assigned_at timestamp without time zone
);

-- Table: users
CREATE TABLE users (
    id integer NOT NULL DEFAULT nextval('users_id_seq'::regclass),
    username character varying(100) NOT NULL,
    email character varying(255),
    full_name character varying(255),
    hashed_password character varying(255) NOT NULL,
    is_active boolean,
    role_id integer,
    phone_number character varying(20)
);

-- Table: ward_types
CREATE TABLE ward_types (
    id integer NOT NULL DEFAULT nextval('ward_types_id_seq'::regclass),
    name character varying(100) NOT NULL,
    code character varying(50),
    description text,
    is_active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone
);

-- Table: wards
CREATE TABLE wards (
    id integer NOT NULL DEFAULT nextval('wards_id_seq'::regclass),
    name character varying(100) NOT NULL,
    ward_number character varying(50),
    ward_type character varying(50),
    capacity integer NOT NULL DEFAULT 0,
    current_occupancy integer NOT NULL DEFAULT 0,
    status USER-DEFINED NOT NULL DEFAULT 'active'::wardstatus,
    floor character varying(50),
    building character varying(100),
    description text,
    charge_per_day numeric NOT NULL DEFAULT 0.00,
    created_at timestamp without time zone DEFAULT now(),
    updated_at timestamp without time zone,
    is_active boolean DEFAULT true
);

