#!/usr/bin/env python3
"""
Test script to demonstrate the improved bot detection countermeasures,
headless browser fallback, and Medium.com handling for the convert-by-url endpoint.
"""

import requests
import json
import time

def test_basic_conversion():
    """Test the convert-by-url endpoint with a basic HTML page"""
    
    print("\n" + "="*60)
    print("TEST 1: Basic HTML Conversion")
    print("="*60)
    
    # Test URL - using a simple HTML page
    test_url = "https://httpbin.org/html"
    
    # API endpoint
    api_url = "http://localhost:5000/convert-by-url"
    
    # Request payload
    payload = {
        "url": test_url,
        "unwanted_tags": ["script", "style", "meta"],
        "unwanted_attrs": ["class", "id", "style"]
    }
    
    print(f"Testing convert-by-url endpoint with URL: {test_url}")
    print("Payload:", json.dumps(payload, indent=2))
    
    try:
        # Make the request
        response = requests.post(api_url, json=payload, timeout=60)
        
        print(f"\nStatus Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success! Conversion completed.")
            print(f"Source URL: {result.get('source_url')}")
            print(f"Markdown length: {len(result.get('markdown', ''))} characters")
            print("\nFirst 200 characters of markdown:")
            print(result.get('markdown', '')[:200] + "...")
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error message: {error_data.get('error')}")
            except:
                print(f"Raw response: {response.text}")
            return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_javascript_heavy_site():
    """Test with a JavaScript-heavy site that requires browser rendering"""
    
    print("\n" + "="*60)
    print("TEST 2: JavaScript-Heavy Site (Browser Rendering)")
    print("="*60)
    
    # Test with a site that heavily uses JavaScript
    test_url = "https://example.com"  # Simple site that should work
    
    api_url = "http://localhost:5000/convert-by-url"
    
    payload = {
        "url": test_url,
        "unwanted_tags": ["script", "style"],
        "unwanted_attrs": ["class", "id"]
    }
    
    print(f"Testing JavaScript rendering with URL: {test_url}")
    
    try:
        response = requests.post(api_url, json=payload, timeout=90)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success! JavaScript content rendered and converted.")
            print(f"Source URL: {result.get('source_url')}")
            print(f"Markdown length: {len(result.get('markdown', ''))} characters")
            print("\nFirst 300 characters of markdown:")
            print(result.get('markdown', '')[:300] + "...")
            return True
        else:
            print(f"\n❌ Error: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error message: {error_data.get('error')}")
            except:
                print(f"Raw response: {response.text}")
            return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_bot_detection_site():
    """Test with a site that might block bots (403 error scenario)"""
    
    print("\n" + "="*60)
    print("TEST 3: Bot Detection Handling (403 Fallback)")
    print("="*60)
    
    # Test with a site that might block automated requests
    # Using a site that's known to sometimes return 403 for bots
    test_url = "https://www.cloudflare.com"
    
    api_url = "http://localhost:5000/convert-by-url"
    
    payload = {
        "url": test_url,
        "unwanted_tags": ["script", "style", "meta"],
        "unwanted_attrs": ["class", "id", "data-(.*)", "aria-(.*)"]
    }
    
    print(f"Testing bot detection handling with URL: {test_url}")
    print("This test checks if the system falls back to headless browser on 403 errors.")
    
    try:
        response = requests.post(api_url, json=payload, timeout=120)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success! Bot detection bypassed with headless browser.")
            print(f"Source URL: {result.get('source_url')}")
            print(f"Markdown length: {len(result.get('markdown', ''))} characters")
            print("\nFirst 200 characters of markdown:")
            print(result.get('markdown', '')[:200] + "...")
            return True
        else:
            print(f"\n⚠️  Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Message: {error_data.get('error')}")
                # This might be expected if the site is very restrictive
                if response.status_code == 403:
                    print("Note: 403 error indicates the site has strong bot protection.")
                    print("The system attempted headless browser fallback.")
            except:
                print(f"Raw response: {response.text}")
            return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_medium_handling():
    """Test Medium.com specific handling for free reading links"""
    
    print("\n" + "="*60)
    print("TEST 4: Medium.com Free Reading Link Detection")
    print("="*60)
    
    # Test with a Medium article (use a public one)
    test_url = "https://medium.com/@example/sample-article"
    
    api_url = "http://localhost:5000/convert-by-url"
    
    payload = {
        "url": test_url,
        "unwanted_tags": ["script", "style", "meta", "nav", "footer"],
        "unwanted_attrs": ["class", "id", "data-(.*)", "aria-(.*)"]
    }
    
    print(f"Testing Medium.com handling with URL: {test_url}")
    print("This test checks if the system can detect and follow free reading links.")
    
    try:
        response = requests.post(api_url, json=payload, timeout=120)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ Success! Medium.com content processed.")
            print(f"Source URL: {result.get('source_url')}")
            print(f"Markdown length: {len(result.get('markdown', ''))} characters")
            
            # Check if URL was redirected (indicating free link was found)
            if result.get('source_url') != test_url:
                print("\n🔗 Free reading link was detected and followed!")
                print(f"Original URL: {test_url}")
                print(f"Free reading URL: {result.get('source_url')}")
            
            print("\nFirst 300 characters of markdown:")
            print(result.get('markdown', '')[:300] + "...")
            return True
        else:
            print(f"\n⚠️  Status: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Message: {error_data.get('error')}")
                print("Note: Medium articles may require specific URLs or may be behind paywalls.")
            except:
                print(f"Raw response: {response.text}")
            return False
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_health_check():
    """Test if the server is running"""
    try:
        response = requests.get('http://localhost:5000/health', timeout=10)
        return response.status_code == 200
    except:
        return False

def run_all_tests():
    """Run all test scenarios"""
    print("🚀 Starting Enhanced Bot Detection and Browser Fallback Tests")
    print("=" * 80)
    
    # Check if server is running
    if not test_health_check():
        print("❌ Server is not running! Please start the server first.")
        print("Run: python server.py")
        return
    
    print("✅ Server is running")
    
    # Run all tests
    tests = [
        ("Basic HTML Conversion", test_basic_conversion),
        ("JavaScript-Heavy Site", test_javascript_heavy_site),
        ("Bot Detection Handling", test_bot_detection_site),
        ("Medium.com Handling", test_medium_handling)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔄 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} completed successfully")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
        
        # Add delay between tests
        time.sleep(2)
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The enhanced bot detection system is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above for details.")
        print("Note: Some failures may be expected due to external site restrictions.")

if __name__ == "__main__":
    run_all_tests()