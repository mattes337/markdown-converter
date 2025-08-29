#!/usr/bin/env python3
"""
Shared conversion utilities for URL dereferencing and content conversion.
Used by both Flask server and Apify actors.
"""

import requests
import tempfile
import os
import re

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin
from markitdown import MarkItDown
from .utils import is_html_content, extract_article_content, clean_html
from .browser_utils import fetch_with_browser_fallback
import logging

logger = logging.getLogger(__name__)

# Initialize MarkItDown
md = MarkItDown()


def dereference_url(url, max_redirects=20):
    """
    Dereference a URL by following redirects and return the final URL.
    
    Args:
        url (str): URL to dereference
        max_redirects (int): Maximum number of redirects to follow
    
    Returns:
        dict: Dictionary containing dereferencing results
    """
    redirect_count = 0
    current_url = url

    redirect_chain = [url]

    # Configure session with headers to avoid bot detection
    session = requests.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': (
            'text/html,application/xhtml+xml,application/xml;'
            'q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
            'application/signed-exchange;v=b3;q=0.7'
        ),
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    })

    while redirect_count < max_redirects:

        try:
            # Try GET request first for better compatibility with tracking services
            response = session.get(
                current_url, allow_redirects=False, timeout=15
            )
            logger.info(
                f"GET {current_url} -> {response.status_code}"
            )
            logger.info(
                f"Response headers: {dict(response.headers)}"
            )

            # Check if this is a redirect response
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get('Location')
                if location:
                    # Handle relative URLs
                    if location.startswith('/'):
                        current_url = urljoin(current_url, location)
                    elif not location.startswith(('http://', 'https://')):
                        current_url = urljoin(current_url, location)
                    else:
                        current_url = location
                    
                    redirect_chain.append(current_url)
                    redirect_count += 1
                    continue
            
            # Check for JavaScript redirects in the content
            if response.status_code == 200 and 'text/html' in response.headers.get('content-type', '').lower():
                try:
                    content = response.text
                    logger.info(
                        f"Checking for JavaScript redirects in HTML "
                        f"content (length: {len(content)})"
                    )

                    # Check if this is a Cloudflare challenge page
                    cf_header = response.headers.get('cf-mitigated', '')
                    if 'cf-mitigated' in cf_header or 'challenge' in content.lower():
                        logger.info(
                            "Detected Cloudflare challenge page - "
                            "cannot follow redirect automatically"
                        )
                        break

                    # Look for common JavaScript redirect patterns
                    js_redirect_patterns = [
                        r'window\.location\.href\s*=\s*["\']([^"\'\']+)["\']',
                        r'window\.location\s*=\s*["\']([^"\'\']+)["\']',
                        r'location\.href\s*=\s*["\']([^"\'\']+)["\']',
                        r'location\s*=\s*["\']([^"\'\']+)["\']',
                        r'document\.location\s*=\s*["\']([^"\'\']+)["\']',
                        r'window\.location\.replace\s*\(\s*["\']([^"\'\']+)["\']\s*\)',
                        r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\'\'\s>]+)',
                        r'location\.replace\s*\(["\']([^"\'\']+)["\']\)',
                        r'window\.open\s*\(["\']([^"\'\']+)["\']',
                        r'href\s*=\s*["\']([^"\'\']+)["\'].*click'
                    ]

                    for pattern in js_redirect_patterns:
                        matches = re.findall(
                            pattern, content, re.IGNORECASE
                        )
                        if matches:
                            for js_url in matches:
                                # Skip obviously non-redirect URLs
                                skip_patterns = [
                                    'javascript:', 'mailto:', '#', 'void(0)'
                                ]
                                if any(skip in js_url.lower()
                                       for skip in skip_patterns):
                                    continue

                                # Handle relative URLs
                                if js_url.startswith('/'):
                                    current_url = urljoin(current_url, js_url)
                                elif not js_url.startswith(
                                    ('http://', 'https://')
                                ):
                                    current_url = urljoin(
                                        current_url, js_url
                                    )
                                else:
                                    current_url = js_url

                                logger.info(
                                    f"Found JavaScript redirect to: {current_url}"
                                )
                                redirect_chain.append(current_url)
                                redirect_count += 1
                                break
                        if matches:
                            break
                    else:
                        # No JavaScript redirect found, we're done
                        logger.info(
                            "No JavaScript redirects found in HTML content"
                        )
                        break
                except Exception:
                    logger.warning("Error parsing JavaScript redirects")
                    break
            else:
                # No redirect and not HTML, we're done
                break

        except requests.RequestException:
            # If request fails, try HEAD request as fallback
            try:
                response = session.head(current_url, allow_redirects=False, timeout=10)
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get('Location')
                    if location:
                        # Handle relative URLs
                        if location.startswith('/'):
                            current_url = urljoin(current_url, location)
                        elif not location.startswith(
                            ('http://', 'https://')
                        ):
                            current_url = urljoin(current_url, location)
                        else:
                            current_url = location

                        redirect_chain.append(current_url)
                        redirect_count += 1
                        continue
                break
            except requests.RequestException:
                # If both GET and HEAD fail, return what we have
                break

    # Clean up tracking parameters from final URL
    parsed_url = urlparse(current_url)

    # Common tracking parameters to remove
    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'twclid', 'li_fat_id',
        '_ga', '_gl', 'mc_cid', 'mc_eid', 'mkt_tok',
        'ref', 'referrer', 'source', 'campaign',
        'igshid', 'ncid', 'cmpid', 'WT.mc_id'
    }

    if parsed_url.query:
        query_params = parse_qs(parsed_url.query, keep_blank_values=True)

        # Remove tracking parameters
        cleaned_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in tracking_params
        }

        # Rebuild URL with cleaned parameters
        new_query = (
            urlencode(cleaned_params, doseq=True) if cleaned_params else ''
        )

        current_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))

    return {
        'success': True,
        'original_url': url,
        'final_url': current_url,
        'redirect_count': redirect_count,
        'redirect_chain': redirect_chain,
        'max_redirects_reached': redirect_count >= max_redirects
    }


def convert_url_to_markdown(url, unwanted_tags=None, unwanted_attrs=None,
                           detect_article=True):
    """
    Convert content from URL to markdown.
    
    Args:
        url (str): URL to convert
        unwanted_tags (list): List of HTML tags to remove
        unwanted_attrs (list): List of HTML attributes to remove
        detect_article (bool): Whether to extract article content
    
    Returns:
        dict: Dictionary containing conversion results
    """
    try:
        # Use browser fallback for handling 403 errors and JS rendering
        html_content, final_url, used_browser, content_type = (
            fetch_with_browser_fallback(url, timeout=30)
        )

        # Convert HTML string to bytes for further processing
        file_content = html_content.encode('utf-8')

        # Update URL to final URL in case of redirects
        url = final_url

        # Log if browser was used
        if used_browser:
            logger.info(f'Used headless browser for {url}')

        # Determine file extension from URL or content-type
        ext = _determine_file_extension(url, content_type)

        # Handle different file types
        content_to_write = file_content

        if ext == '.pdf':
            logger.info('Detected PDF file, fetching binary content')
            content_to_write = _fetch_pdf_content(url)

        elif ext == '.html' or is_html_content(file_content):
            logger.info('Processing HTML content from URL')
            html_content_str = file_content.decode('utf-8', errors='ignore')

            # Extract article content if detect_article flag is set
            if detect_article:
                html_content_str = extract_article_content(html_content_str)

            cleaned_html = clean_html(
                html_content_str, unwanted_tags, unwanted_attrs
            )
            content_to_write = cleaned_html.encode('utf-8')
            ext = '.html'

        # Create temporary file and convert
        return _convert_content_to_markdown(content_to_write, ext, url)

    except Exception as e:
        logger.error(f"Error converting URL {url}: {e}")
        raise


def convert_body_to_markdown(
    content, filename=None, content_type=None, unwanted_tags=None,
    unwanted_attrs=None, detect_article=True
):
    """
    Convert content from request body to markdown.
    
    Args:
        content (bytes): Content to convert
        filename (str): Optional filename to determine extension
        content_type (str): Optional content type
        unwanted_tags (list): List of HTML tags to remove
        unwanted_attrs (list): List of HTML attributes to remove
        detect_article (bool): Whether to extract article content
    
    Returns:
        dict: Dictionary containing conversion results
    """
    try:
        # Determine file extension
        if filename:
            ext = os.path.splitext(filename)[1] or '.bin'
        else:
            ext = _determine_file_extension_from_content_type(
                content_type or ''
            )

        # Check if content is HTML and process it if necessary
        content_to_write = content
        if is_html_content(content):
            logger.info('Detected HTML content, processing it')
            html_content = content.decode('utf-8', errors='ignore')

            # Extract article content if detect_article flag is set
            if detect_article:
                html_content = extract_article_content(html_content)

            cleaned_html = clean_html(
                html_content, unwanted_tags, unwanted_attrs
            )
            content_to_write = cleaned_html.encode('utf-8')
            ext = '.html'

        # Convert to markdown
        return _convert_content_to_markdown(content_to_write, ext)

    except Exception as e:
        logger.error(f"Error converting body content: {e}")
        raise


def _determine_file_extension(url, content_type=None):
    """Determine file extension from URL or content-type"""
    ext = '.html'  # Default to HTML
    url_lower = url.lower()

    # First check URL extension
    if url_lower.endswith('.pdf'):
        ext = '.pdf'
    elif url_lower.endswith(('.docx', '.doc')):
        ext = '.docx'
    elif url_lower.endswith(('.pptx', '.ppt')):
        ext = '.pptx'
    elif url_lower.endswith(('.xlsx', '.xls')):
        ext = '.xlsx'
    elif url_lower.endswith('.csv'):
        ext = '.csv'
    elif url_lower.endswith('.json'):
        ext = '.json'
    elif url_lower.endswith('.xml'):
        ext = '.xml'
    elif url_lower.endswith('.epub'):
        ext = '.epub'
    elif url_lower.endswith('.zip'):
        ext = '.zip'
    elif url_lower.endswith((
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'
    )):
        ext = '.jpg'
    elif url_lower.endswith(('.mp3', '.wav', '.m4a', '.aac')):
        ext = '.mp3'
    elif url_lower.endswith('.txt'):
        ext = '.txt'
    # If no extension found in URL, check content-type header
    elif content_type:
        ext = _determine_file_extension_from_content_type(content_type)

    return ext


def _determine_file_extension_from_content_type(content_type):
    """Determine file extension from content-type header"""
    content_type = content_type.lower()

    if 'pdf' in content_type or content_type == 'application/pdf':
        return '.pdf'
    elif content_type in [
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword'
    ]:
        return '.docx'
    elif content_type in [
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/vnd.ms-powerpoint'
    ]:
        return '.pptx'
    elif content_type in [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel'
    ]:
        return '.xlsx'
    elif content_type == 'text/csv':
        return '.csv'
    elif content_type == 'application/json':
        return '.json'
    elif content_type in ['application/xml', 'text/xml']:
        return '.xml'
    elif content_type == 'application/epub+zip':
        return '.epub'
    elif content_type == 'application/zip':
        return '.zip'
    elif content_type.startswith('image/'):
        return '.jpg'
    elif content_type.startswith('audio/'):
        return '.mp3'
    elif content_type == 'text/plain':
        return '.txt'
    elif 'html' in content_type:
        return '.html'
    else:
        return '.bin'


def _fetch_pdf_content(url):
    """Fetch PDF content from URL"""
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/pdf,*/*'
        }
        pdf_response = requests.get(url, headers=headers, timeout=60)
        pdf_response.raise_for_status()
        logger.info(
            f'Successfully fetched PDF content: '
            f'{len(pdf_response.content)} bytes'
        )
        return pdf_response.content
    except Exception as e:
        logger.error(f'Failed to fetch PDF content: {e}')
        raise


def _convert_content_to_markdown(content, ext, source_url=None):
    """Convert content to markdown using temporary file"""
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(content)
        temp_file_path = temp_file.name

    try:
        # Convert to markdown
        result = md.convert(temp_file_path)
        markdown_content = result.text_content

        response_data = {
            'success': True,
            'markdown': markdown_content
        }

        if source_url:
            response_data['source_url'] = source_url

        return response_data

    finally:
        # Clean up temporary file
        os.unlink(temp_file_path)