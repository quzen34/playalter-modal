#!/usr/bin/env python3
"""
PLAYALTER Simple Test Suite (Windows Compatible)
Basic testing without emoji characters
"""

import requests
import time
import json
import os
from datetime import datetime

def test_playalter_services():
    """Run basic tests on PLAYALTER services"""
    base_url = "https://quzen34--playalter-complete-fastapi-app.modal.run"
    
    print("PLAYALTER Test Suite Starting...")
    print(f"Testing: {base_url}")
    print("=" * 50)
    
    results = []
    
    # Test 1: Health Check
    print("[1/4] Testing health check...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/health", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"  PASS - Health check successful ({response_time:.2f}s)")
            results.append({"test": "health", "status": "PASS", "time": response_time})
        else:
            print(f"  FAIL - Health check failed: {response.status_code}")
            results.append({"test": "health", "status": "FAIL", "error": response.status_code})
    except Exception as e:
        print(f"  FAIL - Health check error: {e}")
        results.append({"test": "health", "status": "FAIL", "error": str(e)})
    
    # Test 2: Homepage
    print("[2/4] Testing homepage...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"  PASS - Homepage loaded ({response_time:.2f}s)")
            results.append({"test": "homepage", "status": "PASS", "time": response_time})
        else:
            print(f"  FAIL - Homepage failed: {response.status_code}")
            results.append({"test": "homepage", "status": "FAIL", "error": response.status_code})
    except Exception as e:
        print(f"  FAIL - Homepage error: {e}")
        results.append({"test": "homepage", "status": "FAIL", "error": str(e)})
    
    # Test 3: Mask Generator Page
    print("[3/4] Testing mask generator page...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/mask-generator", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"  PASS - Mask generator page loaded ({response_time:.2f}s)")
            results.append({"test": "mask_page", "status": "PASS", "time": response_time})
        else:
            print(f"  FAIL - Mask generator page failed: {response.status_code}")
            results.append({"test": "mask_page", "status": "FAIL", "error": response.status_code})
    except Exception as e:
        print(f"  FAIL - Mask generator page error: {e}")
        results.append({"test": "mask_page", "status": "FAIL", "error": str(e)})
    
    # Test 4: Face Swap Page
    print("[4/4] Testing face swap page...")
    try:
        start_time = time.time()
        response = requests.get(f"{base_url}/face-swap", timeout=10)
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"  PASS - Face swap page loaded ({response_time:.2f}s)")
            results.append({"test": "swap_page", "status": "PASS", "time": response_time})
        else:
            print(f"  FAIL - Face swap page failed: {response.status_code}")
            results.append({"test": "swap_page", "status": "FAIL", "error": response.status_code})
    except Exception as e:
        print(f"  FAIL - Face swap page error: {e}")
        results.append({"test": "swap_page", "status": "FAIL", "error": str(e)})
    
    # Calculate summary
    total_tests = len(results)
    passed_tests = len([r for r in results if r["status"] == "PASS"])
    failed_tests = total_tests - passed_tests
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    print("=" * 50)
    
    # Individual results
    print("\nDETAILED RESULTS:")
    for result in results:
        status = result["status"]
        test_name = result["test"]
        if status == "PASS":
            time_info = f" ({result['time']:.2f}s)" if 'time' in result else ""
            print(f"  {test_name}: PASS{time_info}")
        else:
            error_info = f" - {result['error']}" if 'error' in result else ""
            print(f"  {test_name}: FAIL{error_info}")
    
    print(f"\nTesting completed at {datetime.now().strftime('%H:%M:%S')}")
    
    if failed_tests == 0:
        print("SUCCESS: All tests passed! PLAYALTER is working correctly.")
        return True
    else:
        print("WARNING: Some tests failed. Check the detailed results above.")
        return False

if __name__ == "__main__":
    success = test_playalter_services()
    exit(0 if success else 1)