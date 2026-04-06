"""
Lab Enhancement Services
=======================
1. LOINC Code Mapping - Standardized test codes for interoperability
2. Gestational Age Calculator - Essential for neonatal reference ranges
3. Unit Conversion Engine - Support multiple unit systems

Author: LHIMS Lab Module
"""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass


# ==============================================================================
# 1. LOINC CODE MAPPING
# ==============================================================================

# Common LOINC codes for Ghana laboratory tests
LOINC_CODE_MAP = {
    # Haematology
    "Hb": "718-7",  # Hemoglobin [Mass/volume] in Blood
    "HCT": "4544-3",  # Hematocrit [Volume fraction] in Blood
    "WBC": "6690-2",  # Leukocytes [#/volume] in Blood by Count
    "RBC": "789-8",  # Erythrocytes [#/volume] in Blood by Count
    "Platelets": "777-3",  # Platelets [#/volume] in Blood by Count
    "MCV": "787-2",  # Mean corpuscular volume [Entitic volume] in Erythrocytes
    "MCH": "785-6",  # Mean corpuscular hemoglobin [Entitic mass] in Erythrocytes
    "MCHC": "786-4",  # Mean corpuscular hemoglobin concentration [Mass/volume] in Erythrocytes
    "RDW": "788-6",  # Red cell distribution width [Ratio] in Blood
    "Neutrophils": "751-8",  # Neutrophils [#/volume] in Blood by Manual count
    "Lymphocytes": "731-0",  # Lymphocytes [#/volume] in Blood by Count
    "Monocytes": "742-4",  # Monocytes [#/volume] in Blood by Count
    "Eosinophils": "711-2",  # Eosinophils [#/volume] in Blood by Count
    "Basophils": "704-7",  # Basophils [#/volume] in Blood by Count
    "ESR": "30341-2",  # Erythrocyte sedimentation rate
    
    # Chemistry - Liver Function
    "ALT": "1742-6",  # Alanine aminotransferase [Enzyme activity/volume] in Serum or Plasma
    "AST": "1920-8",  # Aspartate aminotransferase [Enzyme activity/volume] in Serum or Plasma
    "ALP": "2208-6",  # Alkaline phosphatase [Enzyme activity/volume] in Serum or Plasma
    "Total Bilirubin": "1975-2",  # Bilirubin.total [Mass/volume] in Serum or Plasma
    "Direct Bilirubin": "1974-5",  # Bilirubin.conjugated [Mass/volume] in Serum or Plasma
    "Total Protein": "2885-2",  # Protein [Mass/volume] in Serum or Plasma
    "Albumin": "1751-7",  # Albumin [Mass/volume] in Serum or Plasma
    "GGT": "2324-2",  # Gamma-glutamyltransferase [Enzyme activity/volume] in Serum or Plasma
    
    # Chemistry - Kidney Function
    "Creatinine": "2160-0",  # Creatinine [Mass/volume] in Serum or Plasma
    "BUN": "3094-0",  # Urea Nitrogen [Mass/volume] in Serum or Plasma
    "Uric Acid": "3084-1",  # Urate [Mass/volume] in Serum or Plasma
    "Sodium": "2951-2",  # Sodium [Moles/volume] in Serum or Plasma
    "Potassium": "2823-3",  # Potassium [Moles/volume] in Serum or Plasma
    "Chloride": "2075-0",  # Chloride [Moles/volume] in Serum or Plasma
    "Bicarbonate": "1968-7",  # Bicarbonate [Moles/volume] in Serum or Plasma
    
    # Chemistry - Lipid Profile
    "Total Cholesterol": "2093-3",  # Cholesterol [Mass/volume] in Serum or Plasma
    "Triglycerides": "2571-8",  # Triglycerides [Mass/volume] in Serum or Plasma
    "HDL": "2085-9",  # Cholesterol.in HDL [Mass/volume] in Serum or Plasma
    "LDL": "2089-1",  # Cholesterol.in LDL [Mass/volume] in Serum or Plasma
    
    # Chemistry - Glucose
    "Fasting Glucose": "1558-6",  # Glucose [Mass/volume] in Blood
    "Random Glucose": "2345-7",  # Glucose [Mass/volume] in Serum or Plasma
    "HbA1c": "4548-4",  # Hemoglobin A1c/Hemoglobin.total in Blood
    
    # Chemistry - Proteins
    "CRP": "1988-5",  # C-reactive protein [Mass/volume] in Serum or Plasma
    "RF": "2410-6",  # Rheumatoid factor [Titer] in Serum or Plasma
    
    # Serology
    "HBsAg": "22322-1",  # Hepatitis B surface antigen [Presence] in Serum or Plasma
    "HBsAb": "22323-9",  # Hepatitis B surface antibody [Units/volume] in Serum or Plasma
    "HCV": "22326-2",  # Hepatitis C virus antibody [Presence] in Serum or Plasma
    "HIV": "42717-5",  # HIV 1+2 Ab [Presence] in Serum or Plasma
    "Syphilis": "4476-5",  # Treponema pallidum Ab [Presence] in Serum or Plasma
    
    # Urinalysis
    "Urine Protein": "2888-6",  # Protein [Mass/volume] in Urine
    "Urine Glucose": "25428-4",  # Glucose [Mass/volume] in Urine
    "Urine Blood": "2335-8",  # Blood [Presence] in Urine
    "Urine Ketones": "2514-8",  # Ketones [Mass/volume] in Urine
    "Urine pH": "2756-6",  # pH in Urine
    "Urine SG": "5817-6",  # Specific gravity in Urine
    
    # Microbiology
    "WBC (CSF)": "595-4",  # Leukocytes [#/volume] in CSF
    "Protein (CSF)": "2339-0",  # Protein [Mass/volume] in CSF
    "Glucose (CSF)",  # Not available in LOINC
}

# Reverse LOINC mapping (code to test name)
LOINC_REVERSE_MAP = {v: k for k, v in LOINC_CODE_MAP.items()}


def get_loinc_code(test_name: str) -> Optional[str]:
    """
    Get LOINC code for a test name.
    
    Args:
        test_name: The test name to look up
        
    Returns:
        LOINC code if found, None otherwise
    """
    # Direct lookup
    if test_name in LOINC_CODE_MAP:
        return LOINC_CODE_MAP[test_name]
    
    # Try case-insensitive lookup
    test_lower = test_name.lower()
    for key, value in LOINC_CODE_MAP.items():
        if key.lower() == test_lower:
            return value
    
    # Try partial match
    for key, value in LOINC_CODE_MAP.items():
        if key.lower() in test_lower or test_lower in key.lower():
            return value
    
    return None


def get_test_name_from_loinc(loinc_code: str) -> Optional[str]:
    """
    Get test name from LOINC code.
    
    Args:
        loinc_code: The LOINC code to look up
        
    Returns:
        Test name if found, None otherwise
    """
    return LOINC_REVERSE_MAP.get(loinc_code)


# ==============================================================================
# 2. GESTATIONAL AGE CALCULATOR
# ==============================================================================

@dataclass
class GestationalAge:
    """Gestational age representation"""
    weeks: int
    days: int
    
    @property
    def total_days(self) -> int:
        return self.weeks * 7 + self.days
    
    def __str__(self) -> str:
        return f"{self.weeks}+{self.days}"


class GestationalAgeCalculator:
    """
    Calculator for gestational age - essential for neonatal reference ranges.
    
    Supports multiple calculation methods:
    - From LMP (Last Menstrual Period)
    - From ultrasound dating
    - From expected delivery date (EDD)
    """
    
    # Gestational age brackets for reference range selection
    PRETERM_BRAKETS = {
        "EXTREMELY_PRETERM": (0, 27),      # < 28 weeks
        "VERY_PRETERM": (28, 31),           # 28-31 weeks
        "MODERATE_PRETERM": (32, 33),       # 32-33 weeks
        "LATE_PRETERM": (34, 36),          # 34-36 weeks
        "TERM": (37, 42),                   # 37-42 weeks (full term)
        "POST_TERM": (43, 52),             # > 42 weeks
    }
    
    @staticmethod
    def from_lmp(lmp_date: date, reference_date: Optional[date] = None) -> GestationalAge:
        """
        Calculate gestational age from Last Menstrual Period.
        
        Args:
            lmp_date: Date of first day of last menstrual period
            reference_date: Date to calculate from (default: today)
            
        Returns:
            GestationalAge object
        """
        if reference_date is None:
            reference_date = date.today()
        
        # Gestational age = days since LMP
        days_since_lmp = (reference_date - lmp_date).days
        
        if days_since_lmp < 0:
            # Future date - return 0
            return GestationalAge(0, 0)
        
        weeks = days_since_lmp // 7
        days = days_since_lmp % 7
        
        return GestationalAge(weeks, days)
    
    @staticmethod
    def from_edd(edd: date, reference_date: Optional[date] = None) -> GestationalAge:
        """
        Calculate gestational age from Expected Delivery Date.
        
        Assumes 280 days (40 weeks) gestation from LMP.
        
        Args:
            edd: Expected Delivery Date (40 weeks from LMP)
            reference_date: Date to calculate from (default: today)
            
        Returns:
            GestationalAge object
        """
        if reference_date is None:
            reference_date = date.today()
        
        # Gestational age = 280 - days until EDD
        days_until_edd = (edd - reference_date).days
        days_since_lmp = 280 - days_until_edd
        
        if days_since_lmp < 0:
            return GestationalAge(0, 0)
        
        weeks = days_since_lmp // 7
        days = days_since_lmp % 7
        
        return GestationalAge(weeks, days)
    
    @staticmethod
    def from_ultrasound(ultrasound_date: date, ultrasound_weeks: int, ultrasound_days: int, 
                        reference_date: Optional[date] = None) -> GestationalAge:
        """
        Calculate gestational age from ultrasound measurement.
        Uses ultrasound dating as more accurate in early pregnancy.
        
        Args:
            ultrasound_date: Date of ultrasound
            ultrasound_weeks: Gestational age in weeks at ultrasound
            ultrasound_days: Additional days
            reference_date: Date to calculate from (default: today)
            
        Returns:
            GestationalAge object
        """
        if reference_date is None:
            reference_date = date.today()
        
        # Gestational age at ultrasound = ultrasound_weeks + ultrasound_days/7
        # Calculate days that have passed since ultrasound
        days_since_ultrasound = (reference_date - ultrasound_date).days
        
        total_days = (ultrasound_weeks * 7 + ultrasound_days) + days_since_ultrasound
        
        if total_days < 0:
            return GestationalAge(0, 0)
        
        weeks = total_days // 7
        days = total_days % 7
        
        return GestationalAge(weeks, days)
    
    @staticmethod
    def get_preterm_category(gestational_age: GestationalAge) -> str:
        """Get preterm category based on gestational age"""
        total_weeks = gestational_age.weeks
        
        for category, (min_wks, max_wks) in GestationalAgeCalculator.PRETERM_BRAKETS.items():
            if min_wks <= total_weeks <= max_wks:
                return category
        
        return "POST_TERM" if total_weeks > 42 else "UNKNOWN"
    
    @staticmethod
    def is_term(gestational_age: GestationalAge) -> bool:
        """Check if gestational age is at term (37-42 weeks)"""
        return 37 <= gestational_age.weeks <= 42


# ==============================================================================
# 3. UNIT CONVERSION ENGINE
# ==============================================================================

@dataclass
class UnitConversion:
    """Unit conversion result"""
    original_value: float
    converted_value: float
    from_unit: str
    to_unit: str
    conversion_factor: float


class UnitConversionEngine:
    """
    Unit conversion engine for common laboratory tests.
    
    Supports conversion between different unit systems commonly used in Ghana:
    - SI units (mol/L) and conventional units (mg/dL)
    - Different concentration units
    """
    
    # Conversion factors: multiply by factor to convert FROM conventional TO SI
    # To convert from SI to conventional, divide by factor
    CONVERSION_FACTORS = {
        # Glucose: mg/dL -> mmol/L (divide by ~18)
        ("glucose", "mg/dL", "mmol/L"): 0.05551,
        ("glucose", "mmol/L", "mg/dL"): 18.0182,
        
        # Cholesterol: mg/dL -> mmol/L (divide by ~38.67)
        ("cholesterol", "mg/dL", "mmol/L"): 0.02586,
        ("cholesterol", "mmol/L", "mg/dL"): 38.67,
        
        # Triglycerides: mg/dL -> mmol/L (divide by ~88.57)
        ("triglycerides", "mg/dL", "mmol/L"): 0.01129,
        ("triglycerides", "mmol/L", "mg/dL"): 88.57,
        
        # Creatinine: mg/dL -> µmol/L (multiply by ~88.4)
        ("creatinine", "mg/dL", "µmol/L"): 88.4,
        ("creatinine", "µmol/L", "mg/dL"): 0.01131,
        
        # Urea: mg/dL -> mmol/L (divide by ~6)
        ("urea", "mg/dL", "mmol/L"): 0.1665,
        ("urea", "mmol/L", "mg/dL"): 6.006,
        
        # Uric Acid: mg/dL -> µmol/L
        ("uric_acid", "mg/dL", "µmol/L"): 59.48,
        ("uric_acid", "µmol/L", "mg/dL"): 0.01681,
        
        # Bilirubin: mg/dL -> µmol/L
        ("bilirubin", "mg/dL", "µmol/L"): 17.1,
        ("bilirubin", "µmol/L", "mg/dL"): 0.05848,
        
        # Protein: g/dL -> g/L
        ("protein", "g/dL", "g/L"): 10.0,
        ("protein", "g/L", "g/dL"): 0.1,
        
        # Albumin: g/dL -> g/L
        ("albumin", "g/dL", "g/L"): 10.0,
        ("albumin", "g/L", "g/dL"): 0.1,
        
        # Hemoglobin: g/dL -> g/L
        ("hemoglobin", "g/dL", "g/L"): 10.0,
        ("hemoglobin", "g/L", "g/dL"): 0.1,
        
        # Sodium: mEq/L -> mmol/L (1:1 for Na+)
        ("sodium", "mEq/L", "mmol/L"): 1.0,
        ("sodium", "mmol/L", "mEq/L"): 1.0,
        
        # Potassium: mEq/L -> mmol/L (1:1 for K+)
        ("potassium", "mEq/L", "mmol/L"): 1.0,
        ("potassium", "mmol/L", "mEq/L"): 1.0,
        
        # Chloride: mEq/L -> mmol/L (1:1 for Cl-)
        ("chloride", "mEq/L", "mmol/L"): 1.0,
        ("chloride", "mmol/L", "mEq/L"): 1.0,
        
        # CO2/HCO3: mEq/L -> mmol/L (1:1)
        ("bicarbonate", "mEq/L", "mmol/L"): 1.0,
        ("bicarbonate", "mmol/L", "mEq/L"): 1.0,
    }
    
    # Standard units for each test type (SI units preferred)
    STANDARD_UNITS = {
        "glucose": "mmol/L",
        "cholesterol": "mmol/L",
        "triglycerides": "mmol/L",
        "creatinine": "µmol/L",
        "urea": "mmol/L",
        "uric_acid": "µmol/L",
        "bilirubin": "µmol/L",
        "protein": "g/L",
        "albumin": "g/L",
        "hemoglobin": "g/L",
        "sodium": "mmol/L",
        "potassium": "mmol/L",
        "chloride": "mmol/L",
        "bicarbonate": "mmol/L",
    }
    
    # Conventional units for display
    CONVENTIONAL_UNITS = {
        "glucose": "mg/dL",
        "cholesterol": "mg/dL",
        "triglycerides": "mg/dL",
        "creatinine": "mg/dL",
        "urea": "mg/dL",
        "uric_acid": "mg/dL",
        "bilirubin": "mg/dL",
        "protein": "g/dL",
        "albumin": "g/dL",
        "hemoglobin": "g/dL",
        "sodium": "mEq/L",
        "potassium": "mEq/L",
        "chloride": "mEq/L",
        "bicarbonate": "mEq/L",
    }
    
    @classmethod
    def convert(cls, value: float, from_unit: str, to_unit: str, 
                test_type: Optional[str] = None) -> Optional[UnitConversion]:
        """
        Convert value from one unit to another.
        
        Args:
            value: The numeric value to convert
            from_unit: Source unit
            to_unit: Target unit
            test_type: Optional test type for disambiguation
            
        Returns:
            UnitConversion object if conversion possible, None otherwise
        """
        if from_unit == to_unit:
            return UnitConversion(value, value, from_unit, to_unit, 1.0)
        
        # Try direct conversion
        key = (test_type or "", from_unit.lower(), to_unit.lower())
        factor = cls.CONVERSION_FACTORS.get(key)
        
        if factor is not None:
            converted = value * factor
            return UnitConversion(value, converted, from_unit, to_unit, factor)
        
        # Try reverse conversion
        reverse_key = (test_type or "", to_unit.lower(), from_unit.lower())
        reverse_factor = cls.CONVERSION_FACTORS.get(reverse_key)
        
        if reverse_factor is not None:
            converted = value / reverse_factor
            return UnitConversion(value, converted, from_unit, to_unit, 1/reverse_factor)
        
        return None
    
    @classmethod
    def get_standard_unit(cls, test_type: str) -> Optional[str]:
        """Get the standard (SI) unit for a test type"""
        return cls.STANDARD_UNITS.get(test_type.lower())
    
    @classmethod
    def get_conventional_unit(cls, test_type: str) -> Optional[str]:
        """Get the conventional unit for a test type"""
        return cls.CONVENTIONAL_UNITS.get(test_type.lower())
    
    @classmethod
    def convert_to_standard(cls, value: float, unit: str, 
                           test_type: str) -> Optional[UnitConversion]:
        """Convert a value to standard SI unit"""
        std_unit = cls.get_standard_unit(test_type)
        if std_unit is None:
            return None
        return cls.convert(value, unit, std_unit, test_type)
    
    @classmethod
    def convert_to_conventional(cls, value: float, unit: str,
                                test_type: str) -> Optional[UnitConversion]:
        """Convert a value to conventional unit"""
        conv_unit = cls.get_conventional_unit(test_type)
        if conv_unit is None:
            return None
        return cls.convert(value, unit, conv_unit, test_type)
    
    @classmethod
    def get_available_units(cls, test_type: str) -> List[str]:
        """Get all available units for a test type"""
        units = set()
        test_lower = test_type.lower()
        
        for (tt, from_unit, to_unit), factor in cls.CONVERSION_FACTORS.items():
            if tt == test_lower or tt == "":
                units.add(from_unit)
                units.add(to_unit)
        
        return sorted(list(units))
    
    @classmethod
    def is_conversion_available(cls, test_type: str, from_unit: str, to_unit: str) -> bool:
        """Check if unit conversion is available for a test"""
        key = (test_type.lower(), from_unit.lower(), to_unit.lower())
        reverse_key = (test_type.lower(), to_unit.lower(), from_unit.lower())
        return key in cls.CONVERSION_FACTORS or reverse_key in cls.CONVERSION_FACTORS


# ==============================================================================
# ENHANCED REFERENCE RANGE LOOKUP
# ==============================================================================

def get_enhanced_reference_range(
    db,
    field_code: str,
    patient_age_days: Optional[int] = None,
    patient_sex: Optional[str] = None,
    patient_gestational_age: Optional[GestationalAge] = None,
    facility_id: Optional[int] = None,
    result_unit: Optional[str] = None,
    convert_unit: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Enhanced reference range lookup that supports:
    - Age and sex-based ranges
    - Gestational age for neonates
    - Automatic unit conversion
    
    Args:
        db: Database session
        field_code: Field code for the test parameter
        patient_age_days: Patient's age in days
        patient_sex: Patient's sex (M/F)
        patient_gestational_age: Gestational age for neonates
        facility_id: Facility ID for multi-facility support
        result_unit: Unit of the result to potentially convert
        convert_unit: Whether to convert to reference range unit
        
    Returns:
        Dictionary with reference range and conversion info
    """
    from app.services.reference_range_engine import get_field_reference_range
    
    # Get base reference range using existing engine
    ref_range_result = get_field_reference_range(
        db=db,
        field_code=field_code,
        patient_age_days=patient_age_days,
        patient_sex=patient_sex,
        facility_id=facility_id
    )
    
    if not ref_range_result:
        return None
    
    result = ref_range_result.to_dict()
    
    # Handle gestational age for preterm infants
    if patient_gestational_age and patient_age_days is not None and patient_age_days < 365:
        # For neonates, check if we need to use gestational age-adjusted ranges
        # This is a simplified implementation - in production would have separate
        # gestational age-based reference range tables
        preterm_category = GestationalAgeCalculator.get_preterm_category(patient_gestational_age)
        result["gestational_age"] = {
            "weeks": patient_gestational_age.weeks,
            "days": patient_gestational_age.days,
            "preterm_category": preterm_category,
            "is_term": GestationalAgeCalculator.is_term(patient_gestational_age)
        }
    
    # Handle unit conversion
    if convert_unit and result_unit and ref_range_result.unit:
        conversion = UnitConversionEngine.convert(
            value=1.0,  # Just checking if conversion is possible
            from_unit=result_unit,
            to_unit=ref_range_result.unit,
            test_type=field_code.lower()
        )
        
        if conversion:
            result["unit_conversion"] = {
                "available": True,
                "from_unit": result_unit,
                "to_unit": ref_range_result.unit,
                "factor": conversion.conversion_factor
            }
        else:
            result["unit_conversion"] = {
                "available": False,
                "warning": f"Cannot convert from {result_unit} to {ref_range_result.unit}"
            }
    else:
        result["unit_conversion"] = {"available": False}
    
    return result


# ==============================================================================
# EXPORT FUNCTIONS FOR LOINC MAPPING
# ==============================================================================

def export_loinc_mapping() -> Dict[str, str]:
    """Export all LOINC code mappings"""
    return LOINC_CODE_MAP.copy()


def import_loinc_from_csv(csv_data: List[Dict[str, str]]) -> int:
    """
    Import LOINC codes from CSV data.
    
    Args:
        csv_data: List of dicts with 'test_name' and 'loinc_code' keys
        
    Returns:
        Number of mappings imported
    """
    count = 0
    for row in csv_data:
        test_name = row.get("test_name")
        loinc_code = row.get("loinc_code")
        
        if test_name and loinc_code:
            LOINC_CODE_MAP[test_name] = loinc_code
            LOINC_REVERSE_MAP[loinc_code] = test_name
            count += 1
    
    return count
