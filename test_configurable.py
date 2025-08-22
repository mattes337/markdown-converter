#!/usr/bin/env python3
"""
Test script to demonstrate the configurable unwanted tags and attributes functionality
with regex matching support.
"""

import requests
import json

# Test HTML content with various tags and attributes
test_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
    <meta charset="utf-8">
    <style>body { color: red; }</style>
</head>
<body>
    <div class="container" id="main" data-test="value" data-id="123" aria-label="main content" aria-hidden="false">
        <h1 style="color: blue;">Hello World</h1>
        <p class="text" data-info="paragraph" onclick="alert('click')" role="text">This is a test paragraph.</p>
        <img src="test.jpg" alt="test" width="100" height="50">
        <script>console.log('test');</script>
        <custom-tag data-custom="value" my-attr="test">Custom content</custom-tag>
    </div>
</body>
</html>
"""

def test_default_behavior():
    """Test with default unwanted tags and attributes"""
    print("\n=== Testing Default Behavior ===")
    
    response = requests.post(
        'http://localhost:5000/clean-html',
        data=test_html.encode('utf-8'),
        headers={'Content-Type': 'text/html'}
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Success! Cleaned HTML:")
        print(result['html'])
    else:
        print(f"Error: {response.status_code} - {response.text}")

def test_custom_tags():
    """Test with custom unwanted tags using regex"""
    print("\n=== Testing Custom Tags (remove custom-* tags) ===")
    
    response = requests.post(
        'http://localhost:5000/clean-html',
        data=test_html.encode('utf-8'),
        headers={
            'Content-Type': 'text/html',
            'unwanted-tags': 'script,style,custom-(.*)'  # Remove script, style, and any custom-* tags
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Success! Cleaned HTML:")
        print(result['html'])
    else:
        print(f"Error: {response.status_code} - {response.text}")

def test_custom_attributes():
    """Test with custom unwanted attributes using regex"""
    print("\n=== Testing Custom Attributes (remove data-* and aria-* attributes) ===")
    
    response = requests.post(
        'http://localhost:5000/clean-html',
        data=test_html.encode('utf-8'),
        headers={
            'Content-Type': 'text/html',
            'unwanted-attrs': 'data-(.*),aria-(.*),onclick,style'  # Remove data-*, aria-*, onclick, style
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("Success! Cleaned HTML:")
        print(result['html'])
    else:
        print(f"Error: {response.status_code} - {response.text}")

def test_convert_by_url_with_config():
    """Test convert-by-url endpoint with configuration"""
    print("\n=== Testing convert-by-url with configuration ===")
    
    # Create a simple HTML string to simulate URL content
    payload = {
        'url': 'https://httpbin.org/html',  # This returns a simple HTML page
        'unwanted_tags': ['script', 'style'],
        'unwanted_attrs': ['data-(.*)', 'class', 'id']
    }
    
    try:
        response = requests.post(
            'http://localhost:5000/convert-by-url',
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("Success! Converted to markdown:")
            print(result['markdown'][:500] + "..." if len(result['markdown']) > 500 else result['markdown'])
        else:
            print(f"Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Network error: {e}")

if __name__ == '__main__':
    print("Testing configurable unwanted tags and attributes with regex support...")
    
    try:
        # Test health endpoint first
        health_response = requests.get('http://localhost:5000/health')
        if health_response.status_code != 200:
            print("Server is not running! Please start the server first.")
            exit(1)
        
        test_default_behavior()
        test_custom_tags()
        test_custom_attributes()
        test_convert_by_url_with_config()
        
        print("\n=== All tests completed! ===")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure the server is running on http://localhost:5000")
    except Exception as e:
        print(f"Unexpected error: {e}")