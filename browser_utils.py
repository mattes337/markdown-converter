#!/usr/bin/env python3
"""
Browser utilities for handling bot detection and JavaScript rendering.
Provides headless browser functionality for cases where regular HTTP requests fail.
"""

import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
import logging
import google.generativeai as genai
import json

logger = logging.getLogger(__name__)

# Configure Gemini AI
def configure_gemini():
    """
    Configure Gemini AI with API key from environment variable.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment variables")
        return False
    
    genai.configure(api_key=api_key)
    return True

def find_free_reading_url_with_ai(url, html_content):
    """
    Use Gemini 1.5-flash to intelligently find free reading URLs in the HTML content.
    
    Args:
        url (str): Original URL
        html_content (str): HTML content to analyze
    
    Returns:
        str or None: Free reading URL if found, None otherwise
    """
    if not configure_gemini():
        logger.warning("Gemini not configured, falling back to regex patterns")
        return None
    
    try:
        # Create the model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Prepare the prompt
        prompt = f"""
        Analyze this HTML content from {url} and find any links that allow free reading or non-member access.
        
        Look for:
        1. Links with text like "Read this story for free", "Continue reading for free", "Free access", "Non-member link"
        2. Links that bypass paywalls or member restrictions
        3. Alternative URLs that provide free access to the same content
        
        Return ONLY a valid URL if found, or "NONE" if no free reading link exists.
        Do not include any explanation, just the URL or "NONE".
        
        HTML content (first 8000 characters):
        {html_content[:8000]}
        """
        
        # Generate response
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        if result == "NONE" or not result:
            return None
            
        # Validate and clean the URL
        if result.startswith('//'):
            result = 'https:' + result
        elif result.startswith('/'):
            result = 'https://medium.com' + result
        elif not result.startswith('http'):
            return None
            
        logger.info(f"AI found free reading URL: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error using Gemini to find free reading URL: {e}")
        return None

def navigate_to_url_with_browser(url):
    """
    Use browser to navigate to and click/follow the specified URL.
    
    Args:
        url (str): URL to navigate to
    
    Returns:
        str: HTML content from the navigated page
    """
    driver = None
    try:
        driver = create_headless_browser()
        
        # Navigate to the URL
        logger.info(f"Navigating to URL with browser: {url}")
        driver.get(url)
        
        # Wait for the page to load
        time.sleep(3)
        
        # Wait for body to be present
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Additional wait for dynamic content
        time.sleep(2)
        
        # Get the fully rendered HTML
        html_content = driver.page_source
        
        return html_content
        
    except Exception as e:
        logger.error(f"Error navigating to URL {url}: {e}")
        raise
    finally:
        if driver:
            driver.quit()

def create_headless_browser():
    """
    Create a headless Chrome browser instance with anti-detection settings.
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    # Add realistic user agent
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        # Use system-installed ChromeDriver
        chromedriver_path = '/usr/local/bin/chromedriver'
        if os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
        else:
            # Fallback to default system PATH
            service = Service()
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Execute script to remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    except Exception as e:
        logger.error(f"Failed to create headless browser: {e}")
        raise

def get_html_with_browser(url, wait_for_js=True, timeout=30):
    """
    Get HTML content using headless browser, allowing JavaScript to render.
    
    Args:
        url (str): URL to fetch
        wait_for_js (bool): Whether to wait for JavaScript to load
        timeout (int): Maximum time to wait in seconds
    
    Returns:
        str: HTML content after JavaScript rendering
    """
    driver = None
    try:
        driver = create_headless_browser()
        
        # Navigate to the URL
        driver.get(url)
        
        if wait_for_js:
            # Wait for the page to load and JavaScript to execute
            time.sleep(3)
            
            # Wait for body to be present
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Additional wait for dynamic content
            time.sleep(2)
        
        # Get the fully rendered HTML
        html_content = driver.page_source
        
        return html_content
        
    except TimeoutException:
        logger.warning(f"Timeout waiting for page to load: {url}")
        if driver:
            return driver.page_source
        raise
    except WebDriverException as e:
        logger.error(f"WebDriver error for {url}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting HTML for {url}: {e}")
        raise
    finally:
        if driver:
            driver.quit()

def handle_medium_com(url, html_content):
    """
    Handle Medium.com specific cases by using AI to detect and follow free reading links.
    
    Args:
        url (str): Original Medium URL
        html_content (str): HTML content from the page
    
    Returns:
        tuple: (new_url, new_html_content) or (original_url, original_html) if no redirect needed
    """
    if 'medium.com' not in url.lower():
        return url, html_content
    
    # Use AI to find free reading URL
    free_url = find_free_reading_url_with_ai(url, html_content)
    
    if free_url:
        try:
            # Use browser to navigate to the free reading link
            logger.info(f"AI found free reading URL, navigating with browser: {free_url}")
            free_html = navigate_to_url_with_browser(free_url)
            return free_url, free_html
        except Exception as e:
            logger.warning(f"Failed to navigate to AI-found free reading link {free_url}: {e}")
            # Fall back to regex patterns if AI approach fails
            return _handle_medium_com_fallback(url, html_content)
    else:
        # Fall back to regex patterns if AI doesn't find anything
        logger.info("AI didn't find free reading URL, trying fallback patterns")
        return _handle_medium_com_fallback(url, html_content)

def _handle_medium_com_fallback(url, html_content):
    """
    Fallback method using regex patterns for Medium.com free reading links.
    
    Args:
        url (str): Original Medium URL
        html_content (str): HTML content from the page
    
    Returns:
        tuple: (new_url, new_html_content) or (original_url, original_html) if no redirect needed
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for links with specific text content
    links = soup.find_all('a', href=True)
    for link in links:
        link_text = link.get_text().lower().strip()
        href = link.get('href')
        
        # Check for specific Medium non-member link patterns
        is_non_member_link = any(phrase in link_text for phrase in [
            'read this story for free',
            'continue reading for free', 
            'read for free',
            'free access',
            'non members',
            'non-members',
            'non-member link',
            '(non-member link)'
        ])
        
        if is_non_member_link:
            # Clean up the URL
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://medium.com' + href
            elif not href.startswith('http'):
                continue
                
            logger.info(f"Found Medium free reading link by fallback method: {href}")
            
            try:
                # Get the content from the free reading link
                free_html = navigate_to_url_with_browser(href)
                return href, free_html
            except Exception as e:
                logger.warning(f"Failed to fetch free reading link {href}: {e}")
                continue
    
    # No free reading link found, return original content
    return url, html_content

def fetch_with_browser_fallback(url, session=None, timeout=30):
    """
    Attempt to fetch URL with regular requests first, fall back to headless browser on 403.
    
    Args:
        url (str): URL to fetch
        session (requests.Session): Optional session to use for regular request
        timeout (int): Timeout in seconds
    
    Returns:
        tuple: (html_content, final_url, used_browser)
    """
    import requests
    
    # First try with regular requests
    try:
        if session:
            response = session.get(url, timeout=timeout)
        else:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            response = requests.get(url, headers=headers, timeout=timeout)
        
        # If we get a 403, use headless browser
        if response.status_code == 403:
            logger.info(f"Got 403 for {url}, falling back to headless browser")
            html_content = get_html_with_browser(url, timeout=timeout)
            
            # Handle Medium.com specific cases
            final_url, html_content = handle_medium_com(url, html_content)
            
            return html_content, final_url, True
        
        response.raise_for_status()
        html_content = response.text
        
        # Handle Medium.com specific cases even for successful requests
        final_url, html_content = handle_medium_com(url, html_content)
        
        # If Medium handling changed the content, we used browser
        used_browser = final_url != url
        
        return html_content, final_url, used_browser
        
    except requests.exceptions.HTTPError as e:
        if '403' in str(e):
            logger.info(f"Got 403 error for {url}, falling back to headless browser")
            html_content = get_html_with_browser(url, timeout=timeout)
            
            # Handle Medium.com specific cases
            final_url, html_content = handle_medium_com(url, html_content)
            
            return html_content, final_url, True
        else:
            raise
    except requests.exceptions.RequestException as e:
        # For other request errors, try browser as last resort
        logger.info(f"Request failed for {url}, trying headless browser: {e}")
        try:
            html_content = get_html_with_browser(url, timeout=timeout)
            
            # Handle Medium.com specific cases
            final_url, html_content = handle_medium_com(url, html_content)
            
            return html_content, final_url, True
        except Exception as browser_error:
            logger.error(f"Both regular request and browser failed for {url}: {browser_error}")
            raise e  # Raise the original request error