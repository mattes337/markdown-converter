#!/usr/bin/env python3
"""
Test script for the specific Medium URL provided by the user.
"""

import requests
import json

def test_medium_url():
    """Test the convert-by-url endpoint with the specific Medium URL"""
    
    print("🧪 Testing Enhanced Bot Detection with Medium Article")
    print("=" * 60)
    
    # The specific URL provided by the user
    test_url = "https://levelup.gitconnected.com/building-three-pipelines-to-select-the-right-llms-for-rag-multi-agent-systems-and-vision-3e47e0563b76"
    
    # API endpoint
    api_url = "http://localhost:5000/convert-by-url"
    
    # Request payload with comprehensive cleaning
    payload = {
        "url": test_url,
        "unwanted_tags": ["script", "style", "meta", "nav", "footer", "header", "aside"],
        "unwanted_attrs": ["class", "id", "data-(.*)", "aria-(.*)", "style", "onclick"]
    }
    
    print(f"Testing URL: {test_url}")
    print("\nThis will test:")
    print("- Bot detection handling (403 fallback)")
    print("- JavaScript rendering for dynamic content")
    print("- Medium paywall bypass if applicable")
    print("- Content extraction and markdown conversion")
    
    print("\n🔄 Processing... (this may take 30-60 seconds)")
    
    try:
        # Make the request with extended timeout for browser processing
        response = requests.post(api_url, json=payload, timeout=120)
        
        print(f"\n📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS! Article processed successfully.")
            print(f"📄 Source URL: {result.get('source_url')}")
            print(f"📝 Markdown length: {len(result.get('markdown', ''))} characters")
            
            # Check if URL was redirected (indicating paywall bypass)
            if result.get('source_url') != test_url:
                print("\n🔓 Paywall bypass detected!")
                print(f"   Original: {test_url[:80]}...")
                print(f"   Accessed: {result.get('source_url')[:80]}...")
            
            # Show content preview
            markdown_content = result.get('markdown', '')
            print("\n📖 Content Preview (first 500 characters):")
            print("-" * 50)
            print(markdown_content[:500])
            if len(markdown_content) > 500:
                print("\n... (content continues)")
            print("-" * 50)
            
            # Check for key indicators of successful processing
            if "pipeline" in markdown_content.lower() and "llm" in markdown_content.lower():
                print("\n🎯 Content validation: Article about LLM pipelines detected ✓")
            
            return True
            
        else:
            print(f"\n❌ ERROR: {response.status_code}")
            try:
                error_data = response.json()
                print(f"Error message: {error_data.get('error')}")
                
                if response.status_code == 403:
                    print("\n💡 Note: This indicates strong bot protection.")
                    print("   The system attempted headless browser fallback.")
                elif response.status_code == 429:
                    print("\n💡 Note: Rate limiting detected. Try again later.")
                    
            except:
                print(f"Raw response: {response.text[:200]}...")
            return False
                
    except requests.exceptions.Timeout:
        print("\n⏰ Request timed out. The site may be very slow or blocking requests.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_medium_url()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Test completed successfully!")
        print("The enhanced bot detection system is working correctly.")
    else:
        print("⚠️  Test encountered issues.")
        print("Check the error messages above for details.")
    print("=" * 60)