#!/usr/bin/env python3
"""
Test Lab Enhancement Services
============================
This script tests the new lab enhancement features:
1. LOINC code mapping
2. Gestational age calculator
3. Unit conversion engine
"""

import sys
import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict, List
from dataclasses import dataclass


# ==============================================================================
# 1. LOINC CODE MAPPING (Inline copy for standalone testing)
# ==============================================================================

LOINC_CODE_MAP = {
    # Haematology
    "Hb": "718-7",
    "Haemoglobin": "718-7",
    "HCT": "4544-3",
    "Hematocrit": "4544-3",
    "WBC": "6690-2",
    "RBC": "789-8",
    "Platelets": "777-3",
    "MCV": "787-2",
    "MCH": "785-6",
    "MCHC": "786-4",
    "RDW": "788-6",
    "Neutrophils": "751-8",
    "Lymphocytes": "731-0",
    "Monocytes": "742-4",
    "Eosinophils": "711-2",
    "Basophils": "704-7",
    "ESR": "30341-2",
    # Chemistry - Liver Function
    "ALT": "1742-6",
    "AST": "1920-8",
    "ALP": "2208-6",
    "Total Bilirubin": "1975-2",
    "Direct Bilirubin": "1974-5",
    "Total Protein": "2885-2",
    "Albumin": "1751-7",
    "GGT": "2324-2",
    # Chemistry - Kidney Function
    "Creatinine": "2160-0",
    "BUN": "3094-0",
    "Uric Acid": "3084-1",
    "Sodium": "2951-2",
    "Potassium": "2823-3",
    "Chloride": "2075-0",
    "Bicarbonate": "1968-7",
    # Chemistry - Lipid Profile
    "Total Cholesterol": "2093-3",
    "Triglycerides": "2571-8",
    "HDL": "2085-9",
    "LDL": "2089-1",
    # Chemistry - Glucose
    "Fasting Glucose": "1558-6",
    "Random Glucose": "2345-7",
    "HbA1c": "4548-4",
}

LOINC_REVERSE_MAP = {v: k for k, v in LOINC_CODE_MAP.items()}


def get_loinc_code(test_name: str) -> Optional[str]:
    if test_name in LOINC_CODE_MAP:
        return LOINC_CODE_MAP[test_name]
    test_lower = test_name.lower()
    for key, value in LOINC_CODE_MAP.items():
        if key.lower() == test_lower:
            return value
    for key, value in LOINC_CODE_MAP.items():
        if key.lower() in test_lower or test_lower in key.lower():
            return value
    return None


def get_test_name_from_loinc(loinc_code: str) -> Optional[str]:
    return LOINC_REVERSE_MAP.get(loinc_code)


# ==============================================================================
# 2. GESTATIONAL AGE CALCULATOR
# ==============================================================================

@dataclass
class GestationalAge:
    weeks: int
    days: int
    
    @property
    def total_days(self) -> int:
        return self.weeks * 7 + self.days
    
    def __str__(self) -> str:
        return f"{self.weeks}+{self.days}"


class GestationalAgeCalculator:
    PRETERM_BRAKETS = {
        "EXTREMELY_PRETERM": (0, 27),
        "VERY_PRETERM": (28, 31),
        "MODERATE_PRETERM": (32, 33),
        "LATE_PRETERM": (34, 36),
        "TERM": (37, 42),
        "POST_TERM": (43, 52),
    }
    
    @staticmethod
    def from_lmp(lmp_date: date, reference_date: Optional[date] = None) -> GestationalAge:
        if reference_date is None:
            reference_date = date.today()
        days_since_lmp = (reference_date - lmp_date).days
        if days_since_lmp < 0:
            return GestationalAge(0, 0)
        weeks = days_since_lmp // 7
        days = days_since_lmp % 7
        return GestationalAge(weeks, days)
    
    @staticmethod
    def from_edd(edd: date, reference_date: Optional[date] = None) -> GestationalAge:
        if reference_date is None:
            reference_date = date.today()
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
        if reference_date is None:
            reference_date = date.today()
        days_since_ultrasound = (reference_date - ultrasound_date).days
        total_days = (ultrasound_weeks * 7 + ultrasound_days) + days_since_ultrasound
        if total_days < 0:
            return GestationalAge(0, 0)
        weeks = total_days // 7
        days = total_days % 7
        return GestationalAge(weeks, days)
    
    @staticmethod
    def get_preterm_category(gestational_age: GestationalAge) -> str:
        total_weeks = gestational_age.weeks
        for category, (min_wks, max_wks) in GestationalAgeCalculator.PRETERM_BRAKETS.items():
            if min_wks <= total_weeks <= max_wks:
                return category
        return "POST_TERM"
    
    @staticmethod
    def is_term(gestational_age: GestationalAge) -> bool:
        return 37 <= gestational_age.weeks <= 42


# ==============================================================================
# 3. UNIT CONVERSION ENGINE
# ==============================================================================

@dataclass
class UnitConversion:
    original_value: float
    converted_value: float
    from_unit: str
    to_unit: str
    conversion_factor: float


class UnitConversionEngine:
    CONVERSION_FACTORS = {
        ("glucose", "mg/dL", "mmol/L"): 0.05551,
        ("glucose", "mmol/L", "mg/dL"): 18.0182,
        ("cholesterol", "mg/dL", "mmol/L"): 0.02586,
        ("cholesterol", "mmol/L", "mg/dL"): 38.67,
        ("triglycerides", "mg/dL", "mmol/L"): 0.01129,
        ("triglycerides", "mmol/L", "mg/dL"): 88.57,
        ("creatinine", "mg/dL", "µmol/L"): 88.4,
        ("creatinine", "µmol/L", "mg/dL"): 0.01131,
        ("urea", "mg/dL", "mmol/L"): 0.1665,
        ("urea", "mmol/L", "mg/dL"): 6.006,
        ("uric_acid", "mg/dL", "µmol/L"): 59.48,
        ("uric_acid", "µmol/L", "mg/dL"): 0.01681,
        ("bilirubin", "mg/dL", "µmol/L"): 17.1,
        ("bilirubin", "µmol/L", "mg/dL"): 0.05848,
        ("protein", "g/dL", "g/L"): 10.0,
        ("protein", "g/L", "g/dL"): 0.1,
        ("albumin", "g/dL", "g/L"): 10.0,
        ("albumin", "g/L", "g/dL"): 0.1,
        ("hemoglobin", "g/dL", "g/L"): 10.0,
        ("hemoglobin", "g/L", "g/dL"): 0.1,
        ("sodium", "mEq/L", "mmol/L"): 1.0,
        ("sodium", "mmol/L", "mEq/L"): 1.0,
        ("potassium", "mEq/L", "mmol/L"): 1.0,
        ("potassium", "mmol/L", "mEq/L"): 1.0,
        ("chloride", "mEq/L", "mmol/L"): 1.0,
        ("chloride", "mmol/L", "mEq/L"): 1.0,
        ("bicarbonate", "mEq/L", "mmol/L"): 1.0,
        ("bicarbonate", "mmol/L", "mEq/L"): 1.0,
    }
    
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
        if from_unit == to_unit:
            return UnitConversion(value, value, from_unit, to_unit, 1.0)
        
        key = (test_type or "", from_unit.lower(), to_unit.lower())
        factor = cls.CONVERSION_FACTORS.get(key)
        
        if factor is not None:
            converted = value * factor
            return UnitConversion(value, converted, from_unit, to_unit, factor)
        
        reverse_key = (test_type or "", to_unit.lower(), from_unit.lower())
        reverse_factor = cls.CONVERSION_FACTORS.get(reverse_key)
        
        if reverse_factor is not None:
            converted = value / reverse_factor
            return UnitConversion(value, converted, from_unit, to_unit, 1/reverse_factor)
        
        return None
    
    @classmethod
    def get_standard_unit(cls, test_type: str) -> Optional[str]:
        return cls.STANDARD_UNITS.get(test_type.lower())
    
    @classmethod
    def get_conventional_unit(cls, test_type: str) -> Optional[str]:
        return cls.CONVENTIONAL_UNITS.get(test_type.lower())
    
    @classmethod
    def get_available_units(cls, test_type: str) -> List[str]:
        units = set()
        test_lower = test_type.lower()
        for (tt, from_unit, to_unit), factor in cls.CONVERSION_FACTORS.items():
            if tt == test_lower or tt == "":
                units.add(from_unit)
                units.add(to_unit)
        return sorted(list(units))
    
    @classmethod
    def is_conversion_available(cls, test_type: str, from_unit: str, to_unit: str) -> bool:
        key = (test_type.lower(), from_unit.lower(), to_unit.lower())
        reverse_key = (test_type.lower(), to_unit.lower(), from_unit.lower())
        return key in cls.CONVERSION_FACTORS or reverse_key in cls.CONVERSION_FACTORS


# ==============================================================================
# TESTS
# ==============================================================================

def test_loinc_mapping():
    """Test LOINC code mapping"""
    print("\n" + "="*60)
    print("TESTING LOINC CODE MAPPING")
    print("="*60)
    
    tests = ["Hb", "Haemoglobin", "ALT", "Creatinine", "Fasting Glucose"]
    print("\nDirect Lookup:")
    for test in tests:
        loinc = get_loinc_code(test)
        print(f"  {test:30} -> {loinc}")
    
    loinc_codes = ["718-7", "1742-6", "2160-0", "1558-6"]
    print("\nReverse Lookup:")
    for code in loinc_codes:
        name = get_test_name_from_loinc(code)
        print(f"  {code:10} -> {name}")


def test_gestational_age_calculator():
    """Test gestational age calculator"""
    print("\n" + "="*60)
    print("TESTING GESTATIONAL AGE CALCULATOR")
    print("="*60)
    
    today = date.today()
    lmp = today - timedelta(weeks=32, days=3)
    ga = GestationalAgeCalculator.from_lmp(lmp, today)
    print(f"\nLMP: {lmp}, Today: {today}")
    print(f"GA: {ga} weeks ({ga.total_days} days)")
    print(f"Category: {GestationalAgeCalculator.get_preterm_category(ga)}")
    print(f"Is Term: {GestationalAgeCalculator.is_term(ga)}")
    
    edd = today + timedelta(weeks=8)
    ga_edd = GestationalAgeCalculator.from_edd(edd, today)
    print(f"\nEDD: {edd}, GA: {ga_edd}")
    
    print("\nPreterm Categories:")
    test_ages = [(24, 0), (30, 0), (33, 0), (35, 0), (39, 0), (43, 0)]
    for weeks, days in test_ages:
        ga = GestationalAge(weeks, days)
        cat = GestationalAgeCalculator.get_preterm_category(ga)
        print(f"  {weeks}+{days}w -> {cat}")


def test_unit_conversion():
    """Test unit conversion engine"""
    print("\n" + "="*60)
    print("TESTING UNIT CONVERSION ENGINE")
    print("="*60)
    
    # Glucose
    result = UnitConversionEngine.convert(100, "mg/dL", "mmol/L", "glucose")
    if result:
        print(f"\n100 mg/dL glucose -> {result.converted_value:.2f} mmol/L")
    
    result = UnitConversionEngine.convert(5.5, "mmol/L", "mg/dL", "glucose")
    if result:
        print(f"5.5 mmol/L glucose -> {result.converted_value:.1f} mg/dL")
    
    # Cholesterol
    result = UnitConversionEngine.convert(200, "mg/dL", "mmol/L", "cholesterol")
    if result:
        print(f"\n200 mg/dL cholesterol -> {result.converted_value:.2f} mmol/L")
    
    # Creatinine
    result = UnitConversionEngine.convert(1.2, "mg/dL", "µmol/L", "creatinine")
    if result:
        print(f"\n1.2 mg/dL creatinine -> {result.converted_value:.1f} µmol/L")
    
    # Hemoglobin
    result = UnitConversionEngine.convert(12.5, "g/dL", "g/L", "hemoglobin")
    if result:
        print(f"\n12.5 g/dL hemoglobin -> {result.converted_value} g/L")
    
    print("\nStandard Units:")
    for test_type in ["glucose", "cholesterol", "creatinine", "hemoglobin"]:
        std = UnitConversionEngine.get_standard_unit(test_type)
        conv = UnitConversionEngine.get_conventional_unit(test_type)
        print(f"  {test_type:15} SI: {std:10} | Conv: {conv}")


def test_conversion_validation():
    """Test conversion validation"""
    print("\n" + "="*60)
    print("TESTING CONVERSION VALIDATION")
    print("="*60)
    
    test_cases = [
        ("glucose", "mg/dL", "mmol/L", True),
        ("glucose", "mmol/L", "mg/dL", True),
        ("glucose", "mmol/L", "g/L", False),
        ("hemoglobin", "g/dL", "g/L", True),
        ("sodium", "mmol/L", "mEq/L", True),
    ]
    
    for test_type, from_u, to_u, expected in test_cases:
        available = UnitConversionEngine.is_conversion_available(test_type, from_u, to_u)
        status = "✓" if available == expected else "✗"
        print(f"  {status} {test_type}: {from_u} -> {to_u} = {available}")


def main():
    print("\n" + "="*60)
    print("LAB ENHANCEMENTS TEST SUITE")
    print("="*60)
    
    test_loinc_mapping()
    test_gestational_age_calculator()
    test_unit_conversion()
    test_conversion_validation()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
