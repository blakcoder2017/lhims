#!/usr/bin/env python3
"""
Comprehensive LHIMS Endpoint and UI Testing Script

This script tests all major endpoints and UI pages in the LHIMS application.
"""

import requests
import json
import time
from datetime import datetime
from urllib.parse import urljoin
from typing import List, Dict, Tuple
import sys

class LHIMSTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.timeout = 10
        self.results = []
        
    def log_result(self, method: str, path: str, status_code: int, 
                  success: bool, error: str = None, response_time: float = 0):
        """Log test result"""
        result = {
            'method': method,
            'path': path,
            'status_code': status_code,
            'success': success,
            'error': error,
            'response_time': response_time
        }
        self.results.append(result)
        
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} {method} {path} - {status_code} ({response_time:.2f}s)")
        if error:
            print(f"    Error: {error}")
    
    def test_endpoint(self, method: str, path: str, data: Dict = None, 
                   expected_status: int = 200) -> bool:
        """Test a single endpoint"""
        url = urljoin(self.base_url, path)
        
        try:
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url)
            else:
                self.log_result(method, path, 0, False, f"Unsupported method: {method}")
                return False
            
            response_time = time.time() - start_time
            
            # Check if response is successful (2xx status codes)
            success = 200 <= response.status_code < 300
            
            self.log_result(method, path, response.status_code, success, 
                        response_time=response_time)
            return success
            
        except requests.exceptions.Timeout:
            self.log_result(method, path, 0, False, "Request timeout")
            return False
        except requests.exceptions.ConnectionError:
            self.log_result(method, path, 0, False, "Connection error")
            return False
        except Exception as e:
            self.log_result(method, path, 0, False, str(e))
            return False
    
    def test_core_endpoints(self):
        """Test core application endpoints"""
        print("\n🔍 Testing Core Endpoints")
        print("=" * 50)
        
        core_endpoints = [
            ("GET", "/", 200),
            ("GET", "/login", 200),
            ("GET", "/docs", 200),
            ("GET", "/openapi.json", 200),
            ("GET", "/redoc", 200),
        ]
        
        for method, path, expected in core_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints")
        print("=" * 50)
        
        auth_endpoints = [
            ("GET", "/login", 200),
            ("POST", "/api/v1/auth/token", 401),  # Should fail without credentials
            ("GET", "/logout", 200),  # Should redirect or handle gracefully
        ]
        
        for method, path, expected in auth_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_patient_endpoints(self):
        """Test patient management endpoints"""
        print("\n👥 Testing Patient Endpoints")
        print("=" * 50)
        
        patient_endpoints = [
            ("GET", "/patients", 401),  # Should require auth
            ("GET", "/patients/create", 401),  # Should require auth
            ("GET", "/patients/1", 401),  # Should require auth
            ("GET", "/api/v1/patients", 401),  # API endpoint
        ]
        
        for method, path, expected in patient_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_clinical_endpoints(self):
        """Test clinical management endpoints"""
        print("\n🏥 Testing Clinical Endpoints")
        print("=" * 50)
        
        clinical_endpoints = [
            # Triage
            ("GET", "/triage", 401),
            ("GET", "/triage/create", 401),
            
            # OPD
            ("GET", "/opd", 401),
            ("GET", "/opd/visits", 401),
            
            # IPD
            ("GET", "/ipd", 401),
            ("GET", "/wards", 401),
            ("GET", "/beds", 401),
            
            # Emergency
            ("GET", "/emergency", 401),
            ("GET", "/emergency/triage", 401),
        ]
        
        for method, path, expected in clinical_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_admin_endpoints(self):
        """Test administrative endpoints"""
        print("\n⚙️ Testing Admin Endpoints")
        print("=" * 50)
        
        admin_endpoints = [
            ("GET", "/admin", 401),
            ("GET", "/admin/users", 401),
            ("GET", "/admin/backup", 401),
            ("GET", "/admin/settings", 401),
            ("GET", "/admin/departments", 401),
            ("GET", "/admin/ward-types", 401),
            ("GET", "/admin/bed-types", 401),
            ("GET", "/admin/service-pricing", 401),
            ("GET", "/admin/diseases", 401),
        ]
        
        for method, path, expected in admin_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_ancillary_endpoints(self):
        """Test ancillary service endpoints"""
        print("\n🔬 Testing Ancillary Service Endpoints")
        print("=" * 50)
        
        ancillary_endpoints = [
            # Laboratory
            ("GET", "/lab", 401),
            ("GET", "/lab/tests", 401),
            ("GET", "/lab/samples", 401),
            
            # Radiology
            ("GET", "/radiology", 401),
            ("GET", "/radiology/studies", 401),
            ("GET", "/radiology/schedule", 401),
            
            # Pharmacy
            ("GET", "/pharmacy", 401),
            ("GET", "/pharmacy/inventory", 401),
            ("GET", "/pharmacy/formulary", 401),
            ("GET", "/pharmacy/suppliers", 401),
        ]
        
        for method, path, expected in ancillary_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_billing_endpoints(self):
        """Test billing and payment endpoints"""
        print("\n💰 Testing Billing Endpoints")
        print("=" * 50)
        
        billing_endpoints = [
            ("GET", "/billing", 401),
            ("GET", "/billing/invoices", 401),
            ("GET", "/patients/1/pay", 401),
            ("GET", "/claims", 401),
            ("GET", "/expenses", 401),
        ]
        
        for method, path, expected in billing_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_reports_endpoints(self):
        """Test reports and analytics endpoints"""
        print("\n📊 Testing Reports Endpoints")
        print("=" * 50)
        
        reports_endpoints = [
            ("GET", "/reports", 401),
            ("GET", "/reports/patient", 401),
            ("GET", "/reports/financial", 401),
            ("GET", "/reports/clinical", 401),
        ]
        
        for method, path, expected in reports_endpoints:
            self.test_endpoint(method, path, expected_status=expected)
    
    def test_static_files(self):
        """Test static file serving"""
        print("\n📁 Testing Static Files")
        print("=" * 50)
        
        static_files = [
            "/static/css/adminlte.min.css",
            "/static/js/jquery.min.js",
            "/static/img/user.png",
        ]
        
        for file_path in static_files:
            self.test_endpoint("GET", file_path, expected_status=200)
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"🧪 Starting Comprehensive LHIMS Testing")
        print(f"🌐 Base URL: {self.base_url}")
        print(f"⏰ Started at: {datetime.now()}")
        print("=" * 60)
        
        # Test all endpoint categories
        self.test_core_endpoints()
        self.test_auth_endpoints()
        self.test_patient_endpoints()
        self.test_clinical_endpoints()
        self.test_admin_endpoints()
        self.test_ancillary_endpoints()
        self.test_billing_endpoints()
        self.test_reports_endpoints()
        self.test_static_files()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r['success'])
        failed_tests = total_tests - successful_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Successful: {successful_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📈 Success Rate: {(successful_tests/total_tests*100):.1f}%")
        
        # Show failed tests
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.results:
                if not result['success']:
                    print(f"   {result['method']} {result['path']} - {result['status_code']} - {result.get('error', 'Unknown error')}")
        
        # Performance summary
        avg_response_time = sum(r['response_time'] for r in self.results) / len(self.results)
        print(f"\n⏱️ Average Response Time: {avg_response_time:.2f}s")
        
        print(f"\n⏰ Completed at: {datetime.now()}")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test LHIMS endpoints and UI pages")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL to test (default: http://localhost:8000)")
    parser.add_argument("--category", choices=["core", "auth", "patients", "clinical", 
                                           "admin", "ancillary", "billing", "reports", "static"],
                       help="Test specific category only")
    
    args = parser.parse_args()
    
    tester = LHIMSTester(args.url)
    
    if args.category:
        # Test specific category
        if args.category == "core":
            tester.test_core_endpoints()
        elif args.category == "auth":
            tester.test_auth_endpoints()
        elif args.category == "patients":
            tester.test_patient_endpoints()
        elif args.category == "clinical":
            tester.test_clinical_endpoints()
        elif args.category == "admin":
            tester.test_admin_endpoints()
        elif args.category == "ancillary":
            tester.test_ancillary_endpoints()
        elif args.category == "billing":
            tester.test_billing_endpoints()
        elif args.category == "reports":
            tester.test_reports_endpoints()
        elif args.category == "static":
            tester.test_static_files()
        
        tester.print_summary()
    else:
        # Run all tests
        tester.run_all_tests()

if __name__ == "__main__":
    main()
