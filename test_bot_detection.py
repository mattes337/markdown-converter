#!/usr/bin/env python3
"""
Test script to demonstrate the improved bot detection countermeasures
for the convert-by-url endpoint.
"""

import requests
import json

def test_convert_by_url():
    """Test the convert-by-url endpoint with a sample URL"""
    
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
    print("\n" + "="*50)
    
    try:
        # Make the request
        response = requests.post(api_url, json=payload, timeout=60)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print("\nSuccess! Conversion completed.")
            print(f"Source URL: {result.get('source_url')}")
            print(f"Markdown length: {len(result.get('markdown', ''))} characters")
            print("\nFirst 200 characters of markdown:")
            print(result.get('markdown', '')[:200] + "...")
        else:
            print(f"\nError: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error message: {error_data.get('error')}")
            except:
                print(f"Raw response: {response.text}")
                
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_convert_by_url()