#!/usr/bin/env python3
"""
Test script to debug Medium.com free reading link detection
with the specific URL that's failing.
"""

import requests
import json
import logging

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_medium_url_debug():
    """Test the specific Medium URL that's failing"""
    
    # The URL from the user's log that's not working
    test_url = "https://levelup.gitconnected.com/building-three-pipelines-to-select-the-right-llms-for-rag-multi-agent-systems-and-vision-3e47e0563b76?source=rss----5517fd7b58a6---4"
    
    print(f"Testing URL: {test_url}")
    print("=" * 80)
    
    # Test the server endpoint
    server_url = "http://localhost:5000/convert-by-url"
    
    payload = {
        "url": test_url,
        "format": "markdown"
    }
    
    try:
        print("Sending request to server...")
        response = requests.post(server_url, json=payload, timeout=60)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response keys: {list(result.keys())}")
            print(f"Success! Converted content length: {len(result.get('content', ''))}")
            print(f"Final URL: {result.get('url', 'N/A')}")
            print(f"Original URL: {result.get('original_url', 'N/A')}")
            print(f"Status: {result.get('status', 'N/A')}")
            print(f"Message: {result.get('message', 'N/A')}")
            
            # Show first 500 characters of content
            content = result.get('content', '')
            if content:
                print("\nFirst 500 characters of converted content:")
                print("-" * 50)
                print(content[:500])
                print("-" * 50)
            else:
                print("No content returned!")
                print(f"Full response: {result}")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_medium_url_debug()