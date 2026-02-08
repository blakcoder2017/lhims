-- LHIMS Complete Database Schema Dump
-- Generated on: 2026-02-07 13:42:17.431512
-- Total Tables: 55
-- Database: PostgreSQL
-- Connection: localhost:5432/lhims
-- Includes: Tables, Columns, Foreign Keys, Indexes, Constraints

-- Table: admission_notes
CREATE TABLE admission_notes (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for admission_notes
ALTER TABLE admission_notes
    ADD CONSTRAINT admission_notes_parent_note_id_fkey
    FOREIGN KEY (parent_note_id)
    REFERENCES admission_notes(id);

ALTER TABLE admission_notes
    ADD CONSTRAINT admission_notes_admission_id_fkey
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

ALTER TABLE admission_notes
    ADD CONSTRAINT admission_notes_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

-- Indexes for admission_notes
CREATE INDEX ix_admission_notes_id
    ON admission_notes(id);


-- Table: admissions
CREATE TABLE admissions (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for admissions
ALTER TABLE admissions
    ADD CONSTRAINT admissions_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_ward_id_fkey
    FOREIGN KEY (ward_id)
    REFERENCES wards(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_bed_id_fkey
    FOREIGN KEY (bed_id)
    REFERENCES beds(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_admitted_by_id_fkey
    FOREIGN KEY (admitted_by_id)
    REFERENCES users(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_discharged_by_id_fkey
    FOREIGN KEY (discharged_by_id)
    REFERENCES users(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_transferred_from_ward_id_fkey
    FOREIGN KEY (transferred_from_ward_id)
    REFERENCES wards(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_transferred_to_ward_id_fkey
    FOREIGN KEY (transferred_to_ward_id)
    REFERENCES wards(id);

ALTER TABLE admissions
    ADD CONSTRAINT admissions_invoice_id_fkey
    FOREIGN KEY (invoice_id)
    REFERENCES invoices(id);

-- Indexes for admissions
CREATE INDEX ix_admissions_admission_number
    ON admissions(admission_number);

CREATE INDEX ix_admissions_id
    ON admissions(id);


-- Table: alembic_version
CREATE TABLE alembic_version (
,
    PRIMARY KEY (version_num)
);

-- Indexes for alembic_version
CREATE UNIQUE INDEX alembic_version_pkc
    ON alembic_version(version_num);


-- Table: antenatal_visits
CREATE TABLE antenatal_visits (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for antenatal_visits
ALTER TABLE antenatal_visits
    ADD CONSTRAINT antenatal_visits_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE antenatal_visits
    ADD CONSTRAINT antenatal_visits_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE antenatal_visits
    ADD CONSTRAINT antenatal_visits_recorded_by_id_fkey
    FOREIGN KEY (recorded_by_id)
    REFERENCES users(id);

-- Indexes for antenatal_visits
CREATE INDEX ix_antenatal_visits_id
    ON antenatal_visits(id);

CREATE INDEX ix_antenatal_visits_patient_id
    ON antenatal_visits(patient_id);


-- Table: audit_logs
CREATE TABLE audit_logs (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for audit_logs
ALTER TABLE audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES users(id);

-- Indexes for audit_logs
CREATE INDEX ix_audit_logs_created_at
    ON audit_logs(created_at);

CREATE INDEX ix_audit_logs_id
    ON audit_logs(id);


-- Table: bed_types
CREATE TABLE bed_types (
,
    PRIMARY KEY (id)
);

-- Indexes for bed_types
CREATE INDEX ix_bed_types_code
    ON bed_types(code);

CREATE UNIQUE INDEX ix_bed_types_id
    ON bed_types(id);

CREATE UNIQUE INDEX ix_bed_types_name
    ON bed_types(name);


-- Table: beds
CREATE TABLE beds (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for beds
ALTER TABLE beds
    ADD CONSTRAINT beds_ward_id_fkey
    FOREIGN KEY (ward_id)
    REFERENCES wards(id);

-- Indexes for beds
CREATE INDEX ix_beds_bed_number
    ON beds(bed_number);

CREATE INDEX ix_beds_id
    ON beds(id);


-- Table: birth_records
CREATE TABLE birth_records (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for birth_records
ALTER TABLE birth_records
    ADD CONSTRAINT birth_records_mother_patient_id_fkey
    FOREIGN KEY (mother_patient_id)
    REFERENCES patients(id);

ALTER TABLE birth_records
    ADD CONSTRAINT birth_records_admission_id_fkey
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

ALTER TABLE birth_records
    ADD CONSTRAINT birth_records_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE birth_records
    ADD CONSTRAINT birth_records_delivered_by_id_fkey
    FOREIGN KEY (delivered_by_id)
    REFERENCES users(id);

ALTER TABLE birth_records
    ADD CONSTRAINT birth_records_assisted_by_id_fkey
    FOREIGN KEY (assisted_by_id)
    REFERENCES users(id);

-- Indexes for birth_records
CREATE INDEX ix_birth_records_birth_number
    ON birth_records(birth_number);

CREATE INDEX ix_birth_records_id
    ON birth_records(id);

CREATE INDEX ix_birth_records_mother_patient_id
    ON birth_records(mother_patient_id);


-- Table: charge_payments
CREATE TABLE charge_payments (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for charge_payments
ALTER TABLE charge_payments
    ADD CONSTRAINT fk_charge_payments_payment_id_payments
    FOREIGN KEY (payment_id)
    REFERENCES payments(id);

ALTER TABLE charge_payments
    ADD CONSTRAINT fk_charge_payments_charge_id_charges
    FOREIGN KEY (charge_id)
    REFERENCES charges(id);

-- Indexes for charge_payments
CREATE INDEX ix_charge_payments_id
    ON charge_payments(id);


-- Table: charges
CREATE TABLE charges (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for charges
ALTER TABLE charges
    ADD CONSTRAINT charges_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE charges
    ADD CONSTRAINT charges_invoice_id_fkey
    FOREIGN KEY (invoice_id)
    REFERENCES invoices(id);

ALTER TABLE charges
    ADD CONSTRAINT charges_lab_order_id_fkey
    FOREIGN KEY (lab_order_id)
    REFERENCES lab_orders(id);

ALTER TABLE charges
    ADD CONSTRAINT charges_prescription_id_fkey
    FOREIGN KEY (prescription_id)
    REFERENCES prescriptions(id);

ALTER TABLE charges
    ADD CONSTRAINT charges_radiology_order_id_fkey
    FOREIGN KEY (radiology_order_id)
    REFERENCES radiology_orders(id);

ALTER TABLE charges
    ADD CONSTRAINT fk_charges_opd_visit
    FOREIGN KEY (opd_visit_id)
    REFERENCES opd_visits(id);

ALTER TABLE charges
    ADD CONSTRAINT fk_charges_admission
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

-- Indexes for charges
CREATE INDEX ix_charges_id
    ON charges(id);


-- Table: departments
CREATE TABLE departments (
,
    PRIMARY KEY (id)
);

-- Indexes for departments
CREATE INDEX ix_departments_code
    ON departments(code);

CREATE UNIQUE INDEX ix_departments_id
    ON departments(id);

CREATE UNIQUE INDEX ix_departments_name
    ON departments(name);


-- Table: diseases
CREATE TABLE diseases (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for diseases
ALTER TABLE diseases
    ADD CONSTRAINT diseases_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

-- Indexes for diseases
CREATE UNIQUE INDEX ix_diseases_id
    ON diseases(id);

CREATE UNIQUE INDEX ix_diseases_name
    ON diseases(name);


-- Table: doctor_duties
CREATE TABLE doctor_duties (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for doctor_duties
ALTER TABLE doctor_duties
    ADD CONSTRAINT doctor_duties_doctor_id_fkey
    FOREIGN KEY (doctor_id)
    REFERENCES users(id);

-- Indexes for doctor_duties
CREATE INDEX ix_doctor_duties_duty_date
    ON doctor_duties(duty_date);

CREATE INDEX ix_doctor_duties_id
    ON doctor_duties(id);


-- Table: drug_administrations
CREATE TABLE drug_administrations (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for drug_administrations
ALTER TABLE drug_administrations
    ADD CONSTRAINT drug_administrations_administered_by_id_fkey
    FOREIGN KEY (administered_by_id)
    REFERENCES users(id);

ALTER TABLE drug_administrations
    ADD CONSTRAINT drug_administrations_admission_id_fkey
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

ALTER TABLE drug_administrations
    ADD CONSTRAINT drug_administrations_prescription_id_fkey
    FOREIGN KEY (prescription_id)
    REFERENCES prescriptions(id);

-- Indexes for drug_administrations
CREATE INDEX ix_drug_administrations_id
    ON drug_administrations(id);


-- Table: drug_interactions
CREATE TABLE drug_interactions (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for drug_interactions
ALTER TABLE drug_interactions
    ADD CONSTRAINT drug_interactions_medication1_id_fkey
    FOREIGN KEY (medication1_id)
    REFERENCES medications(id);

ALTER TABLE drug_interactions
    ADD CONSTRAINT drug_interactions_medication2_id_fkey
    FOREIGN KEY (medication2_id)
    REFERENCES medications(id);

-- Indexes for drug_interactions
CREATE INDEX ix_drug_interactions_id
    ON drug_interactions(id);


-- Table: encounter_diseases
CREATE TABLE encounter_diseases (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for encounter_diseases
ALTER TABLE encounter_diseases
    ADD CONSTRAINT encounter_diseases_disease_id_fkey
    FOREIGN KEY (disease_id)
    REFERENCES diseases(id);

ALTER TABLE encounter_diseases
    ADD CONSTRAINT encounter_diseases_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

-- Indexes for encounter_diseases
CREATE INDEX ix_encounter_diseases_id
    ON encounter_diseases(id);


-- Table: encounters
CREATE TABLE encounters (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for encounters
ALTER TABLE encounters
    ADD CONSTRAINT fk_encounters_opd_visit
    FOREIGN KEY (opd_visit_id)
    REFERENCES opd_visits(id);

ALTER TABLE encounters
    ADD CONSTRAINT fk_encounters_admission
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

ALTER TABLE encounters
    ADD CONSTRAINT encounters_clinician_id_fkey
    FOREIGN KEY (clinician_id)
    REFERENCES users(id);

ALTER TABLE encounters
    ADD CONSTRAINT encounters_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE encounters
    ADD CONSTRAINT encounters_queue_entry_id_fkey
    FOREIGN KEY (queue_entry_id)
    REFERENCES opd_queue(id);

ALTER TABLE encounters
    ADD CONSTRAINT encounters_appointment_id_fkey
    FOREIGN KEY (appointment_id)
    REFERENCES scheduled_appointments(id);

-- Indexes for encounters
CREATE INDEX ix_encounters_id
    ON encounters(id);


-- Table: expenses
CREATE TABLE expenses (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for expenses
ALTER TABLE expenses
    ADD CONSTRAINT expenses_approved_by_id_fkey
    FOREIGN KEY (approved_by_id)
    REFERENCES users(id);

ALTER TABLE expenses
    ADD CONSTRAINT expenses_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

-- Indexes for expenses
CREATE INDEX ix_expenses_expense_number
    ON expenses(expense_number);

CREATE INDEX ix_expenses_id
    ON expenses(id);


-- Table: fluid_balance
CREATE TABLE fluid_balance (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for fluid_balance
ALTER TABLE fluid_balance
    ADD CONSTRAINT fluid_balance_admission_id_fkey
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

ALTER TABLE fluid_balance
    ADD CONSTRAINT fluid_balance_recorded_by_id_fkey
    FOREIGN KEY (recorded_by_id)
    REFERENCES users(id);

-- Indexes for fluid_balance
CREATE INDEX ix_fluid_balance_admission_id
    ON fluid_balance(admission_id);

CREATE INDEX ix_fluid_balance_id
    ON fluid_balance(id);


-- Table: formulary_rules
CREATE TABLE formulary_rules (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for formulary_rules
ALTER TABLE formulary_rules
    ADD CONSTRAINT formulary_rules_medication_id_fkey
    FOREIGN KEY (medication_id)
    REFERENCES medications(id);

-- Indexes for formulary_rules
CREATE INDEX ix_formulary_rules_id
    ON formulary_rules(id);


-- Table: hospital_settings
CREATE TABLE hospital_settings (
,
    PRIMARY KEY (id)
);

-- Indexes for hospital_settings
CREATE INDEX ix_hospital_settings_id
    ON hospital_settings(id);


-- Table: image_annotations
CREATE TABLE image_annotations (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for image_annotations
ALTER TABLE image_annotations
    ADD CONSTRAINT image_annotations_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

ALTER TABLE image_annotations
    ADD CONSTRAINT image_annotations_image_id_fkey
    FOREIGN KEY (image_id)
    REFERENCES radiology_images(id);

-- Indexes for image_annotations
CREATE INDEX ix_image_annotations_id
    ON image_annotations(id);


-- Table: insurance_providers
CREATE TABLE insurance_providers (
,
    PRIMARY KEY (id)
);

-- Indexes for insurance_providers
CREATE INDEX ix_insurance_providers_code
    ON insurance_providers(code);

CREATE UNIQUE INDEX ix_insurance_providers_id
    ON insurance_providers(id);

CREATE UNIQUE INDEX ix_insurance_providers_name
    ON insurance_providers(name);


-- Table: inventory_transactions
CREATE TABLE inventory_transactions (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for inventory_transactions
ALTER TABLE inventory_transactions
    ADD CONSTRAINT inventory_transactions_medication_id_fkey
    FOREIGN KEY (medication_id)
    REFERENCES medications(id);

ALTER TABLE inventory_transactions
    ADD CONSTRAINT inventory_transactions_performed_by_id_fkey
    FOREIGN KEY (performed_by_id)
    REFERENCES users(id);

ALTER TABLE inventory_transactions
    ADD CONSTRAINT inventory_transactions_prescription_id_fkey
    FOREIGN KEY (prescription_id)
    REFERENCES prescriptions(id);

ALTER TABLE inventory_transactions
    ADD CONSTRAINT inventory_transactions_stock_item_id_fkey
    FOREIGN KEY (stock_item_id)
    REFERENCES stock_items(id);

-- Indexes for inventory_transactions
CREATE INDEX ix_inventory_transactions_id
    ON inventory_transactions(id);


-- Table: invoices
CREATE TABLE invoices (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for invoices
ALTER TABLE invoices
    ADD CONSTRAINT invoices_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

ALTER TABLE invoices
    ADD CONSTRAINT invoices_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE invoices
    ADD CONSTRAINT invoices_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE invoices
    ADD CONSTRAINT fk_invoices_opd_visit
    FOREIGN KEY (opd_visit_id)
    REFERENCES opd_visits(id);

ALTER TABLE invoices
    ADD CONSTRAINT fk_invoices_admission
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

ALTER TABLE invoices
    ADD CONSTRAINT invoices_appointment_id_fkey
    FOREIGN KEY (appointment_id)
    REFERENCES scheduled_appointments(id);

-- Indexes for invoices
CREATE UNIQUE INDEX ix_invoices_id
    ON invoices(id);

CREATE UNIQUE INDEX ix_invoices_invoice_number
    ON invoices(invoice_number);


-- Table: lab_orders
CREATE TABLE lab_orders (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for lab_orders
ALTER TABLE lab_orders
    ADD CONSTRAINT lab_orders_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE lab_orders
    ADD CONSTRAINT lab_orders_ordered_by_id_fkey
    FOREIGN KEY (ordered_by_id)
    REFERENCES users(id);

ALTER TABLE lab_orders
    ADD CONSTRAINT lab_orders_result_entered_by_id_fkey
    FOREIGN KEY (result_entered_by_id)
    REFERENCES users(id);

ALTER TABLE lab_orders
    ADD CONSTRAINT fk_lab_orders_patient_id
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE lab_orders
    ADD CONSTRAINT fk_lab_orders_checked_in_by
    FOREIGN KEY (checked_in_by_id)
    REFERENCES users(id);

ALTER TABLE lab_orders
    ADD CONSTRAINT fk_lab_orders_opd_visit
    FOREIGN KEY (opd_visit_id)
    REFERENCES opd_visits(id);

ALTER TABLE lab_orders
    ADD CONSTRAINT fk_lab_orders_admission
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

-- Indexes for lab_orders
CREATE INDEX ix_lab_orders_id
    ON lab_orders(id);


-- Table: lab_samples
CREATE TABLE lab_samples (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for lab_samples
ALTER TABLE lab_samples
    ADD CONSTRAINT lab_samples_collected_by_id_fkey
    FOREIGN KEY (collected_by_id)
    REFERENCES users(id);

ALTER TABLE lab_samples
    ADD CONSTRAINT lab_samples_lab_order_id_fkey
    FOREIGN KEY (lab_order_id)
    REFERENCES lab_orders(id);

ALTER TABLE lab_samples
    ADD CONSTRAINT lab_samples_received_by_id_fkey
    FOREIGN KEY (received_by_id)
    REFERENCES users(id);

-- Indexes for lab_samples
CREATE INDEX ix_lab_samples_barcode
    ON lab_samples(barcode);

CREATE INDEX ix_lab_samples_id
    ON lab_samples(id);


-- Table: lab_tests
CREATE TABLE lab_tests (
,
    PRIMARY KEY (id)
);

-- Indexes for lab_tests
CREATE UNIQUE INDEX ix_lab_tests_id
    ON lab_tests(id);

CREATE INDEX ix_lab_tests_test_code
    ON lab_tests(test_code);

CREATE INDEX ix_lab_tests_test_name
    ON lab_tests(test_name);


-- Table: medications
CREATE TABLE medications (
,
    PRIMARY KEY (id)
);

-- Indexes for medications
CREATE UNIQUE INDEX ix_medications_id
    ON medications(id);

CREATE INDEX ix_medications_medication_code
    ON medications(medication_code);

CREATE INDEX ix_medications_name
    ON medications(name);


-- Table: nhis_claims
CREATE TABLE nhis_claims (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for nhis_claims
ALTER TABLE nhis_claims
    ADD CONSTRAINT nhis_claims_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

ALTER TABLE nhis_claims
    ADD CONSTRAINT nhis_claims_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE nhis_claims
    ADD CONSTRAINT nhis_claims_invoice_id_fkey
    FOREIGN KEY (invoice_id)
    REFERENCES invoices(id);

ALTER TABLE nhis_claims
    ADD CONSTRAINT nhis_claims_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

-- Indexes for nhis_claims
CREATE INDEX ix_nhis_claims_claim_number
    ON nhis_claims(claim_number);

CREATE INDEX ix_nhis_claims_id
    ON nhis_claims(id);


-- Table: opd_queue
CREATE TABLE opd_queue (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for opd_queue
ALTER TABLE opd_queue
    ADD CONSTRAINT opd_queue_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE opd_queue
    ADD CONSTRAINT opd_queue_assigned_clinician_id_fkey
    FOREIGN KEY (assigned_clinician_id)
    REFERENCES users(id);

ALTER TABLE opd_queue
    ADD CONSTRAINT opd_queue_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

-- Indexes for opd_queue
CREATE INDEX ix_opd_queue_id
    ON opd_queue(id);


-- Table: opd_visits
CREATE TABLE opd_visits (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for opd_visits
ALTER TABLE opd_visits
    ADD CONSTRAINT opd_visits_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE opd_visits
    ADD CONSTRAINT fk_opd_visits_queue_entry
    FOREIGN KEY (queue_entry_id)
    REFERENCES opd_queue(id);

ALTER TABLE opd_visits
    ADD CONSTRAINT fk_opd_visits_appointment_id
    FOREIGN KEY (appointment_id)
    REFERENCES scheduled_appointments(id);

-- Indexes for opd_visits
CREATE UNIQUE INDEX ix_opd_visits_id
    ON opd_visits(id);

CREATE UNIQUE INDEX ix_opd_visits_opd_number
    ON opd_visits(opd_number);


-- Table: password_reset_tokens
CREATE TABLE password_reset_tokens (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for password_reset_tokens
ALTER TABLE password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES users(id);

-- Indexes for password_reset_tokens
CREATE UNIQUE INDEX ix_password_reset_tokens_id
    ON password_reset_tokens(id);

CREATE UNIQUE INDEX ix_password_reset_tokens_token
    ON password_reset_tokens(token);


-- Table: patients
CREATE TABLE patients (
,
    PRIMARY KEY (id)
);

-- Indexes for patients
CREATE INDEX ix_patients_first_name
    ON patients(first_name);

CREATE INDEX ix_patients_id
    ON patients(id);

CREATE UNIQUE INDEX ix_patients_last_name
    ON patients(last_name);

CREATE INDEX ix_patients_national_id
    ON patients(national_id);

CREATE UNIQUE INDEX ix_patients_nhis_number
    ON patients(nhis_number);

CREATE INDEX ix_patients_patient_number
    ON patients(patient_number);

CREATE INDEX ix_patients_phone_number
    ON patients(phone_number);


-- Table: payments
CREATE TABLE payments (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for payments
ALTER TABLE payments
    ADD CONSTRAINT payments_invoice_id_fkey
    FOREIGN KEY (invoice_id)
    REFERENCES invoices(id);

ALTER TABLE payments
    ADD CONSTRAINT payments_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE payments
    ADD CONSTRAINT payments_received_by_id_fkey
    FOREIGN KEY (received_by_id)
    REFERENCES users(id);

-- Indexes for payments
CREATE UNIQUE INDEX ix_payments_id
    ON payments(id);

CREATE UNIQUE INDEX ix_payments_payment_number
    ON payments(payment_number);


-- Table: permissions
CREATE TABLE permissions (
,
    PRIMARY KEY (id)
);

-- Indexes for permissions
CREATE INDEX ix_permissions_id
    ON permissions(id);

CREATE UNIQUE INDEX ix_permissions_module
    ON permissions(module);

CREATE UNIQUE INDEX ix_permissions_name
    ON permissions(name);


-- Table: prescriptions
CREATE TABLE prescriptions (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for prescriptions
ALTER TABLE prescriptions
    ADD CONSTRAINT prescriptions_checked_in_by_id_fkey
    FOREIGN KEY (checked_in_by_id)
    REFERENCES users(id);

ALTER TABLE prescriptions
    ADD CONSTRAINT prescriptions_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE prescriptions
    ADD CONSTRAINT prescriptions_prescribed_by_id_fkey
    FOREIGN KEY (prescribed_by_id)
    REFERENCES users(id);

ALTER TABLE prescriptions
    ADD CONSTRAINT prescriptions_dispensed_by_id_fkey
    FOREIGN KEY (dispensed_by_id)
    REFERENCES users(id);

ALTER TABLE prescriptions
    ADD CONSTRAINT prescriptions_medication_id_fkey
    FOREIGN KEY (medication_id)
    REFERENCES medications(id);

ALTER TABLE prescriptions
    ADD CONSTRAINT fk_prescriptions_opd_visit
    FOREIGN KEY (opd_visit_id)
    REFERENCES opd_visits(id);

ALTER TABLE prescriptions
    ADD CONSTRAINT fk_prescriptions_admission
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

-- Indexes for prescriptions
CREATE INDEX ix_prescriptions_id
    ON prescriptions(id);


-- Table: procedure_catalog
CREATE TABLE procedure_catalog (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for procedure_catalog
ALTER TABLE procedure_catalog
    ADD CONSTRAINT procedure_catalog_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

ALTER TABLE procedure_catalog
    ADD CONSTRAINT procedure_catalog_updated_by_id_fkey
    FOREIGN KEY (updated_by_id)
    REFERENCES users(id);

-- Indexes for procedure_catalog
CREATE UNIQUE INDEX ix_procedure_catalog_id
    ON procedure_catalog(id);

CREATE INDEX ix_procedure_catalog_procedure_code
    ON procedure_catalog(procedure_code);

CREATE INDEX ix_procedure_catalog_procedure_name
    ON procedure_catalog(procedure_name);


-- Table: procedures
CREATE TABLE procedures (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for procedures
ALTER TABLE procedures
    ADD CONSTRAINT procedures_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE procedures
    ADD CONSTRAINT procedures_ordered_by_id_fkey
    FOREIGN KEY (ordered_by_id)
    REFERENCES users(id);

ALTER TABLE procedures
    ADD CONSTRAINT procedures_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE procedures
    ADD CONSTRAINT procedures_performed_by_id_fkey
    FOREIGN KEY (performed_by_id)
    REFERENCES users(id);

ALTER TABLE procedures
    ADD CONSTRAINT fk_procedures_checked_in_by
    FOREIGN KEY (checked_in_by_id)
    REFERENCES users(id);

ALTER TABLE procedures
    ADD CONSTRAINT fk_procedures_procedure_catalog_id
    FOREIGN KEY (procedure_catalog_id)
    REFERENCES procedure_catalog(id);

-- Indexes for procedures
CREATE UNIQUE INDEX ix_procedures_id
    ON procedures(id);

CREATE UNIQUE INDEX ix_procedures_procedure_number
    ON procedures(procedure_number);


-- Table: qc_records
CREATE TABLE qc_records (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for qc_records
ALTER TABLE qc_records
    ADD CONSTRAINT qc_records_lab_order_id_fkey
    FOREIGN KEY (lab_order_id)
    REFERENCES lab_orders(id);

ALTER TABLE qc_records
    ADD CONSTRAINT qc_records_performed_by_id_fkey
    FOREIGN KEY (performed_by_id)
    REFERENCES users(id);

ALTER TABLE qc_records
    ADD CONSTRAINT qc_records_sample_id_fkey
    FOREIGN KEY (sample_id)
    REFERENCES lab_samples(id);

-- Indexes for qc_records
CREATE INDEX ix_qc_records_id
    ON qc_records(id);


-- Table: radiology_images
CREATE TABLE radiology_images (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for radiology_images
ALTER TABLE radiology_images
    ADD CONSTRAINT radiology_images_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE radiology_images
    ADD CONSTRAINT radiology_images_radiology_order_id_fkey
    FOREIGN KEY (radiology_order_id)
    REFERENCES radiology_orders(id);

ALTER TABLE radiology_images
    ADD CONSTRAINT radiology_images_uploaded_by_id_fkey
    FOREIGN KEY (uploaded_by_id)
    REFERENCES users(id);

-- Indexes for radiology_images
CREATE INDEX ix_radiology_images_dicom_instance_uid
    ON radiology_images(dicom_instance_uid);

CREATE INDEX ix_radiology_images_dicom_series_uid
    ON radiology_images(dicom_series_uid);

CREATE INDEX ix_radiology_images_dicom_study_uid
    ON radiology_images(dicom_study_uid);

CREATE UNIQUE INDEX ix_radiology_images_id
    ON radiology_images(id);

CREATE UNIQUE INDEX ix_radiology_images_image_number
    ON radiology_images(image_number);


-- Table: radiology_orders
CREATE TABLE radiology_orders (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for radiology_orders
ALTER TABLE radiology_orders
    ADD CONSTRAINT radiology_orders_encounter_id_fkey
    FOREIGN KEY (encounter_id)
    REFERENCES encounters(id);

ALTER TABLE radiology_orders
    ADD CONSTRAINT radiology_orders_ordered_by_id_fkey
    FOREIGN KEY (ordered_by_id)
    REFERENCES users(id);

ALTER TABLE radiology_orders
    ADD CONSTRAINT radiology_orders_report_entered_by_id_fkey
    FOREIGN KEY (report_entered_by_id)
    REFERENCES users(id);

ALTER TABLE radiology_orders
    ADD CONSTRAINT fk_radiology_orders_patient_id
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE radiology_orders
    ADD CONSTRAINT fk_radiology_orders_checked_in_by
    FOREIGN KEY (checked_in_by_id)
    REFERENCES users(id);

ALTER TABLE radiology_orders
    ADD CONSTRAINT fk_radiology_orders_opd_visit
    FOREIGN KEY (opd_visit_id)
    REFERENCES opd_visits(id);

ALTER TABLE radiology_orders
    ADD CONSTRAINT fk_radiology_orders_admission
    FOREIGN KEY (admission_id)
    REFERENCES admissions(id);

-- Indexes for radiology_orders
CREATE INDEX ix_radiology_orders_id
    ON radiology_orders(id);


-- Table: receipts
CREATE TABLE receipts (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for receipts
ALTER TABLE receipts
    ADD CONSTRAINT fk_receipts_payment_id_payments
    FOREIGN KEY (payment_id)
    REFERENCES payments(id);

ALTER TABLE receipts
    ADD CONSTRAINT fk_receipts_patient_id_patients
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE receipts
    ADD CONSTRAINT fk_receipts_invoice_id_invoices
    FOREIGN KEY (invoice_id)
    REFERENCES invoices(id);

ALTER TABLE receipts
    ADD CONSTRAINT fk_receipts_generated_by_id_users
    FOREIGN KEY (generated_by_id)
    REFERENCES users(id);

-- Indexes for receipts
CREATE UNIQUE INDEX ix_receipts_id
    ON receipts(id);

CREATE UNIQUE INDEX ix_receipts_receipt_number
    ON receipts(receipt_number);


-- Table: reference_ranges
CREATE TABLE reference_ranges (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for reference_ranges
ALTER TABLE reference_ranges
    ADD CONSTRAINT reference_ranges_test_id_fkey
    FOREIGN KEY (test_id)
    REFERENCES lab_tests(id);

-- Indexes for reference_ranges
CREATE INDEX ix_reference_ranges_id
    ON reference_ranges(id);

CREATE INDEX ix_reference_ranges_test_code
    ON reference_ranges(test_code);

CREATE INDEX ix_reference_ranges_test_name
    ON reference_ranges(test_name);


-- Table: role_permissions
CREATE TABLE role_permissions (
,
    PRIMARY KEY (role_id, permission_id)
);

-- Foreign Keys for role_permissions
ALTER TABLE role_permissions
    ADD CONSTRAINT role_permissions_permission_id_fkey
    FOREIGN KEY (permission_id)
    REFERENCES permissions(id);

ALTER TABLE role_permissions
    ADD CONSTRAINT role_permissions_role_id_fkey
    FOREIGN KEY (role_id)
    REFERENCES roles(id);


-- Table: roles
CREATE TABLE roles (
,
    PRIMARY KEY (id)
);

-- Indexes for roles
CREATE UNIQUE INDEX ix_roles_id
    ON roles(id);

CREATE UNIQUE INDEX ix_roles_name
    ON roles(name);


-- Table: scheduled_appointments
CREATE TABLE scheduled_appointments (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for scheduled_appointments
ALTER TABLE scheduled_appointments
    ADD CONSTRAINT scheduled_appointments_assigned_doctor_id_fkey
    FOREIGN KEY (assigned_doctor_id)
    REFERENCES users(id);

ALTER TABLE scheduled_appointments
    ADD CONSTRAINT scheduled_appointments_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

ALTER TABLE scheduled_appointments
    ADD CONSTRAINT scheduled_appointments_cancelled_by_id_fkey
    FOREIGN KEY (cancelled_by_id)
    REFERENCES users(id);

-- Indexes for scheduled_appointments
CREATE INDEX ix_scheduled_appointments_id
    ON scheduled_appointments(id);


-- Table: service_pricing
CREATE TABLE service_pricing (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for service_pricing
ALTER TABLE service_pricing
    ADD CONSTRAINT service_pricing_created_by_id_fkey
    FOREIGN KEY (created_by_id)
    REFERENCES users(id);

ALTER TABLE service_pricing
    ADD CONSTRAINT service_pricing_updated_by_id_fkey
    FOREIGN KEY (updated_by_id)
    REFERENCES users(id);

-- Indexes for service_pricing
CREATE INDEX ix_service_pricing_charge_type
    ON service_pricing(charge_type);

CREATE UNIQUE INDEX ix_service_pricing_id
    ON service_pricing(id);

CREATE UNIQUE INDEX ix_service_pricing_service_code
    ON service_pricing(service_code);

CREATE UNIQUE INDEX ix_service_pricing_service_name
    ON service_pricing(service_name);


-- Table: shift_types
CREATE TABLE shift_types (
,
    PRIMARY KEY (id)
);

-- Indexes for shift_types
CREATE INDEX ix_shift_types_code
    ON shift_types(code);

CREATE UNIQUE INDEX ix_shift_types_id
    ON shift_types(id);

CREATE UNIQUE INDEX ix_shift_types_name
    ON shift_types(name);


-- Table: stock_items
CREATE TABLE stock_items (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for stock_items
ALTER TABLE stock_items
    ADD CONSTRAINT stock_items_medication_id_fkey
    FOREIGN KEY (medication_id)
    REFERENCES medications(id);

ALTER TABLE stock_items
    ADD CONSTRAINT stock_items_supplier_id_fkey
    FOREIGN KEY (supplier_id)
    REFERENCES suppliers(id);

-- Indexes for stock_items
CREATE INDEX ix_stock_items_batch_number
    ON stock_items(batch_number);

CREATE INDEX ix_stock_items_id
    ON stock_items(id);


-- Table: suppliers
CREATE TABLE suppliers (
,
    PRIMARY KEY (id)
);

-- Indexes for suppliers
CREATE INDEX ix_suppliers_code
    ON suppliers(code);

CREATE INDEX ix_suppliers_id
    ON suppliers(id);

CREATE INDEX ix_suppliers_name
    ON suppliers(name);


-- Table: triage_vitals
CREATE TABLE triage_vitals (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for triage_vitals
ALTER TABLE triage_vitals
    ADD CONSTRAINT fk_triage_vitals_triage_assigned_by_id_users
    FOREIGN KEY (triage_assigned_by_id)
    REFERENCES users(id);

ALTER TABLE triage_vitals
    ADD CONSTRAINT triage_vitals_patient_id_fkey
    FOREIGN KEY (patient_id)
    REFERENCES patients(id);

ALTER TABLE triage_vitals
    ADD CONSTRAINT triage_vitals_recorded_by_id_fkey
    FOREIGN KEY (recorded_by_id)
    REFERENCES users(id);

-- Indexes for triage_vitals
CREATE INDEX ix_triage_vitals_id
    ON triage_vitals(id);


-- Table: users
CREATE TABLE users (
,
    PRIMARY KEY (id)
);

-- Foreign Keys for users
ALTER TABLE users
    ADD CONSTRAINT users_role_id_fkey
    FOREIGN KEY (role_id)
    REFERENCES roles(id);

-- Indexes for users
CREATE INDEX ix_users_email
    ON users(email);

CREATE UNIQUE INDEX ix_users_id
    ON users(id);

CREATE UNIQUE INDEX ix_users_username
    ON users(username);


-- Table: ward_types
CREATE TABLE ward_types (
,
    PRIMARY KEY (id)
);

-- Indexes for ward_types
CREATE INDEX ix_ward_types_code
    ON ward_types(code);

CREATE UNIQUE INDEX ix_ward_types_id
    ON ward_types(id);

CREATE UNIQUE INDEX ix_ward_types_name
    ON ward_types(name);


-- Table: wards
CREATE TABLE wards (
,
    PRIMARY KEY (id)
);

-- Indexes for wards
CREATE UNIQUE INDEX ix_wards_id
    ON wards(id);

CREATE UNIQUE INDEX ix_wards_name
    ON wards(name);

CREATE UNIQUE INDEX ix_wards_ward_number
    ON wards(ward_number);


