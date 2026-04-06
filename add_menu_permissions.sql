-- SQL Script to add menu permissions to LHIMS database
-- Run this script directly on your database (PostgreSQL/MySQL)

-- First, insert the menu permissions into the permissions table
INSERT INTO permissions (name, description, module, is_active) VALUES
('menu_front_office', 'Access Front Office menu', 'menu', true),
('menu_direct_service', 'Access Direct Service Requests menu', 'menu', true),
('menu_nurse', 'Access Nurse menu', 'menu', true),
('menu_doctor', 'Access Doctor menu', 'menu', true),
('menu_clinical', 'Access Clinical Services menu', 'menu', true),
('menu_opd', 'Access OPD menu', 'menu', true),
('menu_emergency', 'Access Emergency menu', 'menu', true),
('menu_ipd', 'Access IPD menu', 'menu', true),
('menu_patients', 'Access Patients menu', 'menu', true),
('menu_pharmacy', 'Access Pharmacy menu', 'menu', true),
('menu_lab', 'Access Laboratory menu', 'menu', true),
('menu_radiology', 'Access Radiology menu', 'menu', true),
('menu_procedures', 'Access Procedures menu', 'menu', true),
('menu_maternity', 'Access Maternity menu', 'menu', true),
('menu_finance', 'Access Finance menu', 'menu', true),
('menu_reports', 'Access Reports menu', 'menu', true)
ON CONFLICT (name) DO NOTHING;

-- Billing permissions
INSERT INTO permissions (name, description, module, is_active) VALUES
('admission_billing', 'Add charges to patient admissions', 'billing', true),
('billing_view', 'View billing/invoices', 'billing', true),
('billing_payment', 'Process payments/clear bills', 'billing', true)
ON CONFLICT (name) DO NOTHING;

-- Get the permission IDs (for PostgreSQL - use LAST_INSERT_ID() for MySQL)
-- Then assign to Admin role (assuming role_id = 1)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_front_office'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_direct_service'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_nurse'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_doctor'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_clinical'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_opd'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_emergency'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_ipd'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_patients'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_pharmacy'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_lab'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_radiology'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_procedures'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_maternity'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_finance'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'menu_reports'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Grant billing permissions to Admin role
INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'admission_billing'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'billing_view'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions WHERE name = 'billing_payment'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Grant billing permissions to Nurse role (if exists)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM permissions p, roles r 
WHERE p.name = 'admission_billing' AND r.name = 'Nurse'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM permissions p, roles r 
WHERE p.name = 'billing_view' AND r.name = 'Nurse'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Grant billing permissions to Front Office role (if exists)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM permissions p, roles r 
WHERE p.name = 'admission_billing' AND r.name = 'Front Office'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM permissions p, roles r 
WHERE p.name = 'billing_view' AND r.name = 'Front Office'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM permissions p, roles r 
WHERE p.name = 'billing_payment' AND r.name = 'Front Office'
ON CONFLICT (role_id, permission_id) DO NOTHING;
