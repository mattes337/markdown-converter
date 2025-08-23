#!/usr/bin/env python3
"""
Test script for AI-powered Medium.com free reading link detection.
"""

import os
from browser_utils import handle_medium_com, find_free_reading_url_with_ai

def test_ai_medium_detection():
    """
    Test the AI-powered Medium.com free reading link detection.
    """
    # Sample Medium HTML content with a free reading link
    sample_html = """
    <html>
    <body>
        <div class="article-content">
            <h1>Sample Medium Article</h1>
            <p>This is a sample article content...</p>
            <div class="paywall-notice">
                <p>This story is for members only.</p>
                <a href="/p/sample-article?source=read_next_recirc-----abc123-----&sk=def456" class="ag hb">
                    Read this story for free
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    test_url = "https://medium.com/@author/sample-article-abc123"
    
    print("Testing AI-powered Medium.com free reading link detection...")
    print(f"Original URL: {test_url}")
    
    # Check if GEMINI_API_KEY is set
    if not os.getenv('GEMINI_API_KEY'):
        print("\nWARNING: GEMINI_API_KEY environment variable not set.")
        print("The AI functionality will fall back to regex patterns.")
        print("To test AI functionality, set GEMINI_API_KEY environment variable.")
    
    try:
        # Test the AI URL detection
        ai_url = find_free_reading_url_with_ai(test_url, sample_html)
        if ai_url:
            print(f"\nAI found free reading URL: {ai_url}")
        else:
            print("\nAI did not find a free reading URL")
        
        # Test the complete handle_medium_com function
        print("\nTesting complete handle_medium_com function...")
        final_url, final_html = handle_medium_com(test_url, sample_html)
        
        if final_url != test_url:
            print(f"Successfully found and would navigate to: {final_url}")
        else:
            print("No free reading link found, using original content")
            
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ai_medium_detection()