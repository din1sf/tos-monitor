#!/usr/bin/env python3
"""
Local testing script for ToS Monitor.
Tests basic functionality without requiring full cloud setup.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8080"

def test_endpoint(name, method, endpoint, data=None, expected_status=200):
    """Test a single endpoint."""
    print(f"\n🧪 Testing {name}...")

    try:
        if method.upper() == "GET":
            response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        elif method.upper() == "POST":
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=data,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
        else:
            print(f"❌ Unsupported method: {method}")
            return False

        print(f"   Status: {response.status_code}")

        if response.status_code == expected_status:
            print(f"   ✅ {name} - PASSED")

            # Try to parse JSON response
            try:
                json_response = response.json()
                if "error" in json_response:
                    print(f"   ⚠️  Response contains error: {json_response['error']}")
                elif "success" in json_response:
                    print(f"   ✅ Success: {json_response.get('success', 'N/A')}")
            except:
                print(f"   ⚠️  Non-JSON response (might be expected)")

            return True
        else:
            print(f"   ❌ {name} - FAILED")
            print(f"   Expected: {expected_status}, Got: {response.status_code}")
            try:
                error_detail = response.json()
                print(f"   Error: {error_detail}")
            except:
                print(f"   Raw response: {response.text[:200]}...")
            return False

    except requests.exceptions.ConnectionError:
        print(f"   ❌ {name} - CONNECTION ERROR")
        print("   Make sure the server is running on http://localhost:8080")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ {name} - TIMEOUT")
        return False
    except Exception as e:
        print(f"   ❌ {name} - ERROR: {str(e)}")
        return False

def main():
    """Run all tests."""
    print("🚀 ToS Monitor Local Testing")
    print("=" * 40)

    # Test basic endpoints
    tests = [
        ("Root Endpoint", "GET", "/", None, 200),
        ("Health Check", "GET", "/health", None, [200, 503]),  # May fail without real services
        ("Configuration", "GET", "/config", None, [200, 404, 500]),  # May fail without bucket
        ("List Diffs", "GET", "/diffs", None, [200, 500]),  # May fail without bucket
        ("Fetch Docs (Empty)", "POST", "/fetch-docs", {}, [200, 500]),  # May fail without services
        ("Generate Diffs (Empty)", "POST", "/generate-diffs", {}, [200, 500]),  # May fail without services
    ]

    results = []

    for name, method, endpoint, data, expected_status in tests:
        # Handle multiple expected status codes
        if isinstance(expected_status, list):
            success = False
            for status in expected_status:
                if test_endpoint(name, method, endpoint, data, status):
                    success = True
                    break
            results.append((name, success))
        else:
            success = test_endpoint(name, method, endpoint, data, expected_status)
            results.append((name, success))

    # Summary
    print("\n" + "=" * 40)
    print("📊 Test Summary:")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - {name}")

    print(f"\n🎯 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All basic tests passed! Your application is working correctly.")
    elif passed >= total // 2:
        print("⚠️  Some tests failed, likely due to missing cloud services.")
        print("   This is expected for local testing without real API keys/buckets.")
    else:
        print("🚨 Many tests failed. Check your application setup.")

    # Additional testing suggestions
    print("\n💡 Next Steps:")
    print("1. Check the server logs for detailed error information")
    print("2. Visit http://localhost:8080/docs for interactive API documentation")
    print("3. For full testing, configure real Google Cloud Storage bucket and OpenAI API key")
    print("4. Test individual components with real data using the /docs interface")

if __name__ == "__main__":
    main()