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
    logger.debug(f"Starting AI analysis for URL: {url}")
    logger.debug(f"HTML content length: {len(html_content)} characters")
    
    if not configure_gemini():
        logger.warning("Gemini not configured, falling back to regex patterns")
        return None
    
    try:
        # Create the model
        model = genai.GenerativeModel('gemini-1.5-flash')
        logger.debug("Gemini model created successfully")
        
        # Log a sample of the HTML content for debugging
        sample_html = html_content[:2000]
        logger.debug(f"HTML sample for AI analysis: {sample_html[:500]}...")
        
        # Check if HTML contains any obvious free reading indicators
        free_indicators = ['read this story for free', 'continue reading for free', 'free access', 'non-member', 'non members']
        found_indicators = [indicator for indicator in free_indicators if indicator.lower() in html_content.lower()]
        logger.debug(f"Found free reading indicators in HTML: {found_indicators}")
        
        # Prepare the prompt
        prompt = f"""
        Analyze this HTML content from {url} and find any links that allow free reading or non-member access.
        
        Look for:
        1. Links with text like "Read this story for free", "Continue reading for free", "Free access", "Non-member link"
        2. Links that bypass paywalls or member restrictions
        3. Alternative URLs that provide free access to the same content
        4. Links with href attributes that contain "source=" or similar parameters
        
        Return ONLY a valid URL if found, or "NONE" if no free reading link exists.
        Do not include any explanation, just the URL or "NONE".
        
        HTML content (first 8000 characters):
        {html_content[:8000]}
        """
        
        logger.debug("Sending request to Gemini AI...")
        # Generate response
        response = model.generate_content(prompt)
        result = response.text.strip()
        
        logger.debug(f"Gemini AI response: '{result}'")
        
        if result == "NONE" or not result:
            logger.debug("AI returned NONE or empty result")
            return None
            
        # Validate and clean the URL
        original_result = result
        if result.startswith('//'):
            result = 'https:' + result
        elif result.startswith('/'):
            result = 'https://medium.com' + result
        elif not result.startswith('http'):
            logger.debug(f"AI result '{original_result}' is not a valid URL format")
            return None
            
        logger.info(f"AI found free reading URL: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error using Gemini to find free reading URL: {e}")
        logger.debug(f"Full exception details: {str(e)}")
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
    logger.info(f"Starting Medium.com processing for URL: {url}")
    
    # Check if this is a Medium.com URL or Medium partner site
    medium_domains = [
        'medium.com',
        'levelup.gitconnected.com',
        'towardsdatascience.com',
        'betterprogramming.pub',
        'javascript.plainenglish.io',
        'python.plainenglish.io',
        'blog.devgenius.io',
        'codeburst.io',
        'hackernoon.com'
    ]
    
    is_medium_url = any(domain in url.lower() for domain in medium_domains)
    
    if not is_medium_url:
        logger.debug(f"URL {url} is not a Medium.com or partner URL, skipping processing")
        return url, html_content
    
    logger.debug(f"Detected Medium/partner URL: {url}")
    
    logger.debug(f"Processing Medium.com URL with HTML content length: {len(html_content)}")
    
    # Use AI to find free reading URL
    logger.info("Attempting AI-powered free reading URL detection...")
    free_url = find_free_reading_url_with_ai(url, html_content)
    
    if free_url:
        try:
            # Use browser to navigate to the free reading link
            logger.info(f"AI found free reading URL, navigating with browser: {free_url}")
            free_html = navigate_to_url_with_browser(free_url)
            logger.info(f"Successfully retrieved content from AI-found URL: {free_url}")
            return free_url, free_html
        except Exception as e:
            logger.warning(f"Failed to navigate to AI-found free reading link {free_url}: {e}")
            # Fall back to regex patterns if AI approach fails
            logger.info("Falling back to regex pattern matching...")
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
    logger.debug(f"Starting fallback analysis for URL: {url}")
    logger.debug(f"HTML content length: {len(html_content)} characters")
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for links with specific text content
    links = soup.find_all('a', href=True)
    logger.debug(f"Found {len(links)} links in HTML content")
    
    # Log all link texts for debugging
    link_texts = []
    for i, link in enumerate(links[:20]):  # Log first 20 links
        link_text = link.get_text().lower().strip()
        href = link.get('href')
        link_texts.append(f"Link {i+1}: '{link_text}' -> {href}")
    
    logger.debug(f"Sample link texts: {link_texts}")
    
    # Define search patterns
    search_patterns = [
        'read this story for free',
        'continue reading for free', 
        'read for free',
        'free access',
        'non members',
        'non-members',
        'non-member link',
        '(non-member link)',
        'link'
    ]
    
    logger.debug(f"Searching for patterns: {search_patterns}")
    
    for i, link in enumerate(links):
        link_text = link.get_text().lower().strip()
        href = link.get('href')
        
        logger.debug(f"Analyzing link {i+1}: text='{link_text}', href='{href}'")
        
        # Check for specific Medium non-member link patterns
        matching_patterns = [phrase for phrase in search_patterns if phrase in link_text]
        
        if matching_patterns:
            logger.debug(f"Link {i+1} matches patterns: {matching_patterns}")
            
            # Clean up the URL
            original_href = href
            if href.startswith('//'):
                href = 'https:' + href
            elif href.startswith('/'):
                href = 'https://medium.com' + href
            elif not href.startswith('http'):
                logger.debug(f"Skipping link {i+1} - invalid URL format: {original_href}")
                continue
                
            logger.info(f"Found Medium free reading link by fallback method: {href}")
            
            try:
                # Get the content from the free reading link
                free_html = navigate_to_url_with_browser(href)
                return href, free_html
            except Exception as e:
                logger.warning(f"Failed to fetch free reading link {href}: {e}")
                continue
        else:
            logger.debug(f"Link {i+1} does not match any patterns")
    
    # Check if HTML contains the word "link" anywhere (broader search)
    if 'link' in html_content.lower():
        logger.debug("HTML contains the word 'link' - checking for any potential free reading indicators")
        
        # Look for any link that might be a free reading link based on URL patterns
        for i, link in enumerate(links):
            href = link.get('href')
            if href and ('source=' in href or 'sk=' in href or 'friend_link' in href):
                logger.debug(f"Found potential free reading link by URL pattern: {href}")
                
                # Clean up the URL
                if href.startswith('//'):
                    href = 'https:' + href
                elif href.startswith('/'):
                    href = 'https://medium.com' + href
                elif href.startswith('http'):
                    pass  # Already valid
                else:
                    continue
                    
                logger.info(f"Found Medium free reading link by URL pattern: {href}")
                
                try:
                    # Get the content from the free reading link
                    free_html = navigate_to_url_with_browser(href)
                    return href, free_html
                except Exception as e:
                    logger.warning(f"Failed to fetch free reading link {href}: {e}")
                    continue
    
    # No free reading link found, return original content
    logger.debug("No free reading links found in fallback analysis")
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