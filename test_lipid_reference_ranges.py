#!/usr/bin/env python3
"""
Test script to verify reference range engine works correctly with
the updated Lipid Profile reference ranges.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DEBUG", "false")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.reference_range_engine import get_field_reference_range

DATABASE_URL = "postgresql+psycopg2://postgres:password123@localhost:5433/lhims"

def test_range(field_code, age_days, sex, expected_high, expected_low=None, desc=""):
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    result = get_field_reference_range(db, field_code, age_days, sex)
    db.close()
    
    if result is None:
        print(f"  ❌ {field_code}: No range found!")
        return False
    
    # Check high value
    high_ok = expected_high is None or (result.high is not None and abs(float(result.high) - expected_high) < 0.15)
    low_ok = expected_low is None or (result.low is not None and abs(float(result.low) - expected_low) < 0.15)
    
    if high_ok and low_ok:
        print(f"  ✅ {field_code}: {result.text_range}")
        return True
    else:
        print(f"  ❌ {field_code}: Expected high={expected_high}, got {result.high}; Expected low={expected_low}, got {result.low}")
        print(f"      Text: {result.text_range}")
        return False

def main():
    print("\n" + "="*60)
    print("Testing Lipid Profile Reference Ranges")
    print("="*60)
    
    passed = 0
    failed = 0
    
    # Test 1: Adult Male
    print("\n1. Adult Male (35 years)")
    if test_range("total_cholesterol", 35*365, "M", 5.2): passed += 1
    else: failed += 1
    if test_range("hdl_cholesterol", 35*365, "M", None, 1.0): passed += 1
    else: failed += 1
    if test_range("triglycerides", 35*365, "M", 1.7): passed += 1
    else: failed += 1
    if test_range("c_risk_ratio", 35*365, "M", 4.5): passed += 1
    else: failed += 1
    
    # Test 2: Adult Female
    print("\n2. Adult Female (35 years)")
    if test_range("total_cholesterol", 35*365, "F", 5.2): passed += 1
    else: failed += 1
    if test_range("hdl_cholesterol", 35*365, "F", None, 1.3): passed += 1
    else: failed += 1
    if test_range("c_risk_ratio", 35*365, "F", 4.0): passed += 1
    else: failed += 1
    
    # Test 3: Child Male
    print("\n3. Child Male (10 years)")
    if test_range("total_cholesterol", 10*365, "M", 4.4): passed += 1
    else: failed += 1
    if test_range("hdl_cholesterol", 10*365, "M", None, 1.1): passed += 1
    else: failed += 1
    if test_range("triglycerides", 10*365, "M", 1.1): passed += 1
    else: failed += 1
    if test_range("c_risk_ratio", 10*365, "M", 3.0): passed += 1
    else: failed += 1
    
    # Test 4: Child Female
    print("\n4. Child Female (8 years)")
    if test_range("total_cholesterol", 8*365, "F", 4.4): passed += 1
    else: failed += 1
    if test_range("hdl_cholesterol", 8*365, "F", None, 1.1): passed += 1
    else: failed += 1
    if test_range("c_risk_ratio", 8*365, "F", 3.0): passed += 1
    else: failed += 1
    
    # Test 5: Elderly Male
    print("\n5. Elderly Male (70 years)")
    if test_range("c_risk_ratio", 70*365, "M", 4.5): passed += 1
    else: failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
