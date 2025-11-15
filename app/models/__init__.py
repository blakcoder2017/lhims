# This file makes the 'models' folder a Python package.

# Import Base from the database config
from app.db.database import Base

# Import all your models so Alembic can see them
from app.models.patient_models import Patient, PaymentMechanism
from app.models.user_models import User, Role
from app.models.triage_models import TriageVitals
from app.models.appointment_models import Appointment, AppointmentStatus, AppointmentType
from app.models.encounter_models import (
    Encounter, EncounterStatus,
    LabOrder, RadiologyOrder, Prescription, OrderStatus
)
from app.models.billing_models import (
    Invoice, InvoiceStatus,
    Charge, ChargeType,
    Payment, PaymentMethod, PaymentStatus
)
from app.models.inventory_models import (
    Medication, StockItem, StockStatus,
    InventoryTransaction, TransactionType,
    FormularyRule, DrugInteraction
)
from app.models.lab_models import (
    LabSample, SampleStatus,
    QCRecord, QCStatus,
    ReferenceRange
)
from app.models.lab_catalog_models import LabTest
from app.models.supplier_models import Supplier
from app.models.audit_models import AuditLog, AuditAction
from app.models.claims_models import NHISClaim, ClaimStatus
from app.models.pacs_models import RadiologyImage, ImageAnnotation, ImageStatus, ImageType
from app.models.password_reset_models import PasswordResetToken
from app.models.hospital_settings_models import HospitalSettings
from app.models.service_pricing_models import ServicePricing
from app.models.permission_models import Permission
from app.models.ipd_models import (
    Ward, WardStatus,
    Bed, BedStatus,
    Admission, AdmissionStatus,
    DoctorDuty,
    DepartmentType,
    AdmissionNote
)
from app.models.insurance_provider_models import InsuranceProvider
from app.models.ward_type_models import WardType
from app.models.expense_models import Expense, ExpenseCategory, ExpenseStatus
from app.models.procedure_models import Procedure, ProcedureType, ProcedureStatus
from app.models.department_models import Department
from app.models.shift_type_models import ShiftType
from app.models.bed_type_models import BedType
from app.models.drug_administration_models import DrugAdministration
from app.models.disease_models import Disease, EncounterDisease