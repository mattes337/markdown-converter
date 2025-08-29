#!/usr/bin/env python3
"""
Apify Actor for Google Search to Markdown conversion.
This actor searches Google using SERP API and converts the results to Markdown format.
"""

import os
import sys
import json
import asyncio
import requests
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from apify import Actor
from bs4 import BeautifulSoup
from urllib.parse import urlencode, urlparse, unquote

# Add the shared directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from conversion_utils import convert_url_to_markdown


async def search_google_serp(search_query, max_results=5, get_recent=False, country_code="US", language_code="en"):
    """
    Search Google using Apify's Google SERP proxy.
    
    Args:
        search_query (str): The search query
        max_results (int): Maximum number of results to return
        get_recent (bool): Whether to prioritize recent results
        country_code (str): Country code for search localization
        language_code (str): Language code for search results
    
    Returns:
        list: List of search results with URLs, titles, and snippets
    """
    # Get proxy password from environment
    proxy_password = os.getenv('APIFY_PROXY_PASSWORD')
    if not proxy_password:
        Actor.log.error("APIFY_PROXY_PASSWORD environment variable not set")
        return []
    
    # Map country codes to Google domains
    domain_map = {
        "US": "google.com",
        "GB": "google.co.uk",
        "DE": "google.de",
        "FR": "google.fr",
        "ES": "google.es",
        "IT": "google.it",
        "CA": "google.ca",
        "AU": "google.com.au",
        "IN": "google.co.in",
        "JP": "google.co.jp"
    }
    
    google_domain = domain_map.get(country_code, "google.com")
    
    # Prepare search parameters
    search_params = {
        'q': search_query,
        'num': min(max_results, 100),  # Google limits to 100 results per page
        'hl': language_code
    }
    
    # Add date filter for recent results
    if get_recent:
        search_params['tbs'] = 'qdr:m'  # Last month
    
    # Build the search URL
    search_url = f"http://www.{google_domain}/search?{urlencode(search_params)}"
    
    # Configure proxy
    proxy_config = {
        'http': 'http://groups-GOOGLE_SERP:{}@proxy.apify.com:8000'.format(proxy_password),
        'https': 'http://groups-GOOGLE_SERP:{}@proxy.apify.com:8000'.format(proxy_password)
    }
    
    try:
        Actor.log.info(f"Making request to: {search_url}")
        Actor.log.info(f"Using proxy config: http://groups-GOOGLE_SERP:***@proxy.apify.com:8000")
        
        # Make request through Google SERP proxy
        response = requests.get(
            search_url,
            proxies=proxy_config,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            timeout=30
        )
        
        Actor.log.info(f"Response status code: {response.status_code}")
        Actor.log.info(f"Response headers: {dict(response.headers)}")
        Actor.log.info(f"Response content length: {len(response.text)}")
        
        response.raise_for_status()
        
        # Log first 1000 characters of response for debugging
        Actor.log.info(f"Response content preview: {response.text[:1000]}...")
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Log page title for verification
        page_title = soup.find('title')
        Actor.log.info(f"Page title: {page_title.get_text() if page_title else 'No title found'}")
        
        # Check for various possible result containers
        search_results_g = soup.find_all('div', class_='g')
        search_results_rc = soup.find_all('div', class_='rc')
        search_results_tF2Cxc = soup.find_all('div', class_='tF2Cxc')
        search_results_MjjYud = soup.find_all('div', class_='MjjYud')
        
        Actor.log.info(f"Found result containers - g: {len(search_results_g)}, rc: {len(search_results_rc)}, tF2Cxc: {len(search_results_tF2Cxc)}, MjjYud: {len(search_results_MjjYud)}")
        
        # Try different selectors
        search_results = search_results_g or search_results_tF2Cxc or search_results_MjjYud or search_results_rc
        
        if not search_results:
            # Log all div classes to help identify the correct selector
            all_divs = soup.find_all('div', class_=True)
            div_classes = set()
            for div in all_divs[:50]:  # Limit to first 50 divs
                if div.get('class'):
                    div_classes.update(div.get('class'))
            Actor.log.info(f"Found div classes in page: {sorted(list(div_classes))}")
            
            # Check for CAPTCHA or blocked content
            if 'captcha' in response.text.lower() or 'blocked' in response.text.lower():
                Actor.log.error("Detected CAPTCHA or blocked content in response")
            
            # Check for "did you mean" or no results messages
            if 'did not match any documents' in response.text or 'No results found' in response.text:
                Actor.log.warning("Google returned 'no results found' message")
        
        # Extract search results
        results = []
        
        for i, result in enumerate(search_results[:max_results]):
            Actor.log.info(f"Processing result {i+1}: {result.get('class')}")
            
            # Try multiple selectors for title and URL
            title_elem = result.find('h3') or result.find('h2') or result.find('h1')
            link_elem = result.find('a')
            
            if not title_elem:
                Actor.log.warning(f"No title element found in result {i+1}")
                continue
                
            if not link_elem:
                Actor.log.warning(f"No link element found in result {i+1}")
                continue
            
            title = title_elem.get_text(strip=True)
            url = link_elem.get('href')
            
            Actor.log.info(f"Raw URL from result {i+1}: {url}")
            
            # Clean up URL (remove Google redirect and decode)
            if url and url.startswith('/url?q='):
                url = unquote(url.split('/url?q=')[1].split('&')[0])
                Actor.log.info(f"Cleaned redirect URL: {url}")
            elif url and url.startswith('http'):
                url = unquote(url)
                Actor.log.info(f"Decoded URL: {url}")
            
            # Extract snippet with multiple selectors
            snippet_elem = (result.find('span', class_=['st', 'aCOpRe']) or 
                          result.find('div', class_=['s', 'st']) or
                          result.find('span', class_='VwiC3b') or
                          result.find('div', class_='VwiC3b'))
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            
            # Extract displayed link
            cite_elem = result.find('cite')
            displayed_link = cite_elem.get_text(strip=True) if cite_elem else ""
            
            if url and title:
                result_data = {
                    "url": url,
                    "title": title,
                    "snippet": snippet,
                    "displayedLink": displayed_link
                }
                results.append(result_data)
                Actor.log.info(f"Added result {i+1}: {title[:50]}... -> {url}")
            else:
                Actor.log.warning(f"Skipping result {i+1} - missing URL or title")
        
        Actor.log.info(f"Successfully extracted {len(results)} search results for query: {search_query}")
        return results[:max_results]
    
    except Exception as e:
        Actor.log.error(f"Error searching Google SERP: {str(e)}")
        return []


async def scrape_and_convert_url(url, unwanted_tags=None, unwanted_attrs=None):
    """
    Scrape a URL and convert its content to markdown.
    
    Args:
        url (str): URL to scrape
        unwanted_tags (list): HTML tags to remove
        unwanted_attrs (list): HTML attributes to remove
    
    Returns:
        dict: Dictionary with markdown content, title, and metadata
    """
    try:
        # Use the shared conversion utility
        result = convert_url_to_markdown(
            url,
            unwanted_tags=unwanted_tags or [],
            unwanted_attrs=unwanted_attrs or []
        )
        
        if result.get('success'):
            return {
                "markdown": result['markdown'],
                "url": url,
                "title": None,  # Title extraction would need to be added to conversion_utils
                "publish_date": None,  # Publish date extraction would need to be added
                "success": True,
                "error": None
            }
        else:
            return {
                "markdown": None,
                "url": url,
                "title": None,
                "publish_date": None,
                "success": False,
                "error": "Conversion failed"
            }
    
    except Exception as e:
        Actor.log.error(f"Error converting URL {url}: {str(e)}")
        return {
            "markdown": None,
            "url": url,
            "title": None,
            "publish_date": None,
            "success": False,
            "error": str(e)
        }


async def main():
    """
    Main actor function that processes search to markdown conversion requests.
    """
    async with Actor:
        # Get input from Apify
        actor_input = await Actor.get_input() or {}
        
        # Extract required parameters
        search_query = actor_input.get('searchQuery')
        if not search_query:
            await Actor.fail('Missing required parameter: searchQuery')
            return
        
        max_results = actor_input.get('maxResults', 5)
        get_recent = actor_input.get('getRecent', False)
        country_code = actor_input.get('countryCode', 'US')
        language_code = actor_input.get('languageCode', 'en')
        unwanted_tags = actor_input.get('unwantedTags', [])
        unwanted_attrs = actor_input.get('unwantedAttrs', [])
        
        Actor.log.info(f"Starting search for query: '{search_query}' with {max_results} results (recent: {get_recent}, country: {country_code}, language: {language_code})")
        
        try:
            # Step 1: Search Google using SERP API
            search_results = await search_google_serp(search_query, max_results, get_recent, country_code, language_code)
            
            if not search_results:
                Actor.log.warning("No search results found")
                await Actor.push_data({
                    'search_query': search_query,
                    'max_results': max_results,
                    'get_recent': get_recent,
                    'results': [],
                    'success': False,
                    'error': 'No search results found'
                })
                return
            
            Actor.log.info(f"Found {len(search_results)} search results")
            
            # Step 2: Scrape and convert each URL to markdown
            converted_results = []
            
            for i, search_result in enumerate(search_results):
                Actor.log.info(f"Processing result {i+1}/{len(search_results)}: {search_result['url']}")
                
                # Convert URL to markdown
                conversion_result = await scrape_and_convert_url(
                    search_result['url'],
                    unwanted_tags,
                    unwanted_attrs
                )
                
                # Combine search result metadata with conversion result
                final_result = {
                    'markdown': conversion_result['markdown'],
                    'url': search_result['url'],
                    'title': search_result['title'],  # Use title from search results
                    'publish_date': conversion_result.get('publish_date'),
                    'snippet': search_result.get('snippet', ''),
                    'success': conversion_result['success'],
                    'error': conversion_result.get('error')
                }
                
                converted_results.append(final_result)
                
                # Push individual result to dataset
                await Actor.push_data(final_result)
            
            # Push summary result
            summary = {
                'search_query': search_query,
                'max_results': max_results,
                'get_recent': get_recent,
                'total_found': len(search_results),
                'successful_conversions': len([r for r in converted_results if r['success']]),
                'failed_conversions': len([r for r in converted_results if not r['success']]),
                'results': converted_results,
                'success': True
            }
            
            await Actor.push_data(summary)
            Actor.log.info(f"Completed processing. Successfully converted {summary['successful_conversions']}/{summary['total_found']} results")
        
        except Exception as e:
            Actor.log.error(f"Actor failed with error: {str(e)}")
            await Actor.push_data({
                'search_query': search_query,
                'max_results': max_results,
                'get_recent': get_recent,
                'results': [],
                'success': False,
                'error': str(e)
            })
            await Actor.fail(f"Actor execution failed: {str(e)}")


if __name__ == '__main__':
    asyncio.run(main())