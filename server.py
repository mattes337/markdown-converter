# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
import requests
import tempfile
import os
import re
import time
import random
import gzip
import zlib
import logging
from markitdown import MarkItDown
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from browser_utils import fetch_with_browser_fallback

# Try to import brotli, but don't fail if it's not available
try:
    import brotli
    BROTLI_AVAILABLE = True
except ImportError:
    BROTLI_AVAILABLE = False

# Configure logging
# Get log level from environment variable, default to INFO
log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = getattr(logging, log_level_str, logging.INFO)

logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Set specific loggers to appropriate levels
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('markitdown').setLevel(log_level)

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Initialize MarkItDown
md = MarkItDown()


def is_html_content(content):
    """Check if content is HTML by looking for HTML tags"""
    content_str = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else str(content)
    return any(tag in content_str.lower() for tag in ['<html', '<body', '<div', '<p', '<span', '<!doctype'])

def extract_article_content(html_content):
    """Extract content from <article> tag if present, otherwise return original content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Look for article tag
    article = soup.find('article')
    if article:
        return str(article)
    
    # No article tag found, return original content
    return html_content

def clean_html(html_content, unwanted_tags=None, unwanted_attrs=None):
    """Clean HTML content by removing unwanted tags and attributes"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Default unwanted tags if not provided
    if unwanted_tags is None:
        unwanted_tags = ['head', 'img', 'script', 'style', 'meta', 'link', 'noscript', 'iframe', 'embed', 'object']
    
    # Default unwanted attributes if not provided
    if unwanted_attrs is None:
        unwanted_attrs = ['style', 'class', 'id', 'onclick', 'onload', 'onerror', 'data-(.*)', 'width', 'height', 'valign', 'role', 'align', 'cellspacing', 'border', 'cellpadding', 'aria-(.*)']
    
    # Remove unwanted tags completely (support regex patterns)
    for tag_pattern in unwanted_tags:
        if '*' in tag_pattern or '(' in tag_pattern:
            # Regex pattern
            regex = re.compile(tag_pattern.replace('*', '.*'))
            for element in soup.find_all():
                if element.name and regex.match(element.name):
                    element.decompose()
        else:
            # Exact match
            for element in soup.find_all(tag_pattern):
                element.decompose()
    
    # Remove unwanted attributes from all tags (support regex patterns)
    for tag in soup.find_all():
        for attr in list(tag.attrs.keys()):
            should_remove = False
            for attr_pattern in unwanted_attrs:
                if '*' in attr_pattern or '(' in attr_pattern:
                    # Regex pattern
                    regex = re.compile(attr_pattern.replace('*', '.*'))
                    if regex.match(attr):
                        should_remove = True
                        break
                else:
                    # Exact match
                    if attr == attr_pattern:
                        should_remove = True
                        break
            
            if should_remove:
                del tag.attrs[attr]
    
    # Remove empty tags
    for tag in soup.find_all():
        if not tag.get_text(strip=True) and not tag.find_all() and tag.name not in ['br', 'hr', 'img']:
            tag.decompose()
    
    return str(soup)

@app.route('/clean-html', methods=['POST'])
def route_clean_html():
    try:
        if not request.data:
            return jsonify({'error': 'File data is required in request body'}), 400

        # Get configuration from headers or use defaults
        unwanted_tags = None
        unwanted_attrs = None
        detect_article = request.headers.get('detect-article', 'true').lower() == 'true'
        
        if 'unwanted-tags' in request.headers:
            unwanted_tags = request.headers.get('unwanted-tags').split(',')
            unwanted_tags = [tag.strip() for tag in unwanted_tags if tag.strip()]
        
        if 'unwanted-attrs' in request.headers:
            unwanted_attrs = request.headers.get('unwanted-attrs').split(',')
            unwanted_attrs = [attr.strip() for attr in unwanted_attrs if attr.strip()]

        # Check if content is HTML and clean it if necessary
        content_to_write = request.data
        if is_html_content(request.data):
            app.logger.info('Detected HTML content, cleaning it')
            html_content = request.data.decode('utf-8', errors='ignore')
            cleaned_html = clean_html(html_content, unwanted_tags, unwanted_attrs)

            return jsonify({
                'success': True,
                'html': cleaned_html
            })

        return jsonify({'success': False, 'error': 'NotHTML'}), 400

    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500


@app.route('/convert-by-url', methods=['POST'])
def convert_by_url():
    try:
        # Get URL from JSON body
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in JSON body'}), 400
        
        url = data['url']
        
        # Get configuration from JSON body or use defaults
        unwanted_tags = data.get('unwanted_tags')
        unwanted_attrs = data.get('unwanted_attrs')
        detect_article = data.get('detect_article', True)
        
        # Use browser fallback for handling 403 errors and JavaScript rendering
        html_content, final_url, used_browser, content_type = fetch_with_browser_fallback(url, timeout=30)
        
        # Convert HTML string to bytes for further processing
        file_content = html_content.encode('utf-8')
        
        # Update URL to final URL in case of redirects (e.g., Medium free links)
        url = final_url
        
        # Log if browser was used
        if used_browser:
            app.logger.info(f'Used headless browser for {url}')
        
        # Determine file extension from URL or content-type
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
        elif url_lower.endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')):
            ext = '.jpg'
        elif url_lower.endswith(('.mp3', '.wav', '.m4a', '.aac')):
            ext = '.mp3'
        elif url_lower.endswith('.txt'):
            ext = '.txt'
        # If no extension found in URL, check content-type header
        elif content_type:
            if 'pdf' in content_type or content_type == 'application/pdf':
                ext = '.pdf'
                app.logger.info(f'Detected PDF from content-type: {content_type}')
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                ext = '.docx'
            elif content_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint']:
                ext = '.pptx'
            elif content_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                ext = '.xlsx'
            elif content_type == 'text/csv':
                ext = '.csv'
            elif content_type == 'application/json':
                ext = '.json'
            elif content_type in ['application/xml', 'text/xml']:
                ext = '.xml'
            elif content_type == 'application/epub+zip':
                ext = '.epub'
            elif content_type == 'application/zip':
                ext = '.zip'
            elif content_type.startswith('image/'):
                ext = '.jpg'
            elif content_type.startswith('audio/'):
                ext = '.mp3'
            elif content_type == 'text/plain':
                ext = '.txt'
        
        # Handle different file types
        content_to_write = file_content
        
        if ext == '.pdf':
            app.logger.info('Detected PDF file, fetching binary content')
            # For PDF files, we need to fetch the actual binary content
            try:
                import requests
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/pdf,*/*'
                }
                pdf_response = requests.get(url, headers=headers, timeout=60)
                pdf_response.raise_for_status()
                content_to_write = pdf_response.content
                app.logger.info(f'Successfully fetched PDF content: {len(content_to_write)} bytes')
            except Exception as e:
                app.logger.error(f'Failed to fetch PDF content: {e}')
                return jsonify({'error': f'Failed to fetch PDF content: {str(e)}'}), 500
                
        elif ext == '.html' or is_html_content(file_content):
            app.logger.info('Processing HTML content from URL')
            html_content_str = file_content.decode('utf-8', errors='ignore')
            
            # Extract article content if detect_article flag is set
            if detect_article:
                html_content_str = extract_article_content(html_content_str)
            
            cleaned_html = clean_html(html_content_str, unwanted_tags, unwanted_attrs)
            content_to_write = cleaned_html.encode('utf-8')
            ext = '.html'
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(content_to_write)
            temp_file_path = temp_file.name

        try:
            # Convert to markdown
            result = md.convert(temp_file_path)
            markdown_content = result.text_content
            
            return jsonify({
                'success': True,
                'markdown': markdown_content,
                'source_url': url
            })
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    except requests.RequestException as e:
        error_msg = str(e)
        status_code = 400
        
        # Provide more specific error messages for common scenarios
        if '403' in error_msg or 'Forbidden' in error_msg:
            error_msg = f'Access forbidden (403) - Bot detection or access restrictions detected. Tried headless browser fallback. Original error: {error_msg}'
            status_code = 403
        elif '429' in error_msg or 'Too Many Requests' in error_msg:
            error_msg = f'Rate limited (429) - Too many requests. Please try again later. Original error: {error_msg}'
            status_code = 429
        elif 'timeout' in error_msg.lower():
            error_msg = f'Request timeout - The server took too long to respond. Original error: {error_msg}'
            status_code = 408
        else:
            error_msg = f'Failed to download file: {error_msg}'
            
        return jsonify({'error': error_msg}), status_code
    except ImportError as e:
        if 'selenium' in str(e).lower() or 'webdriver' in str(e).lower():
            error_msg = 'Headless browser functionality not available. Please install selenium and webdriver-manager dependencies.'
            return jsonify({'error': error_msg}), 500
        else:
            return jsonify({'error': f'Import error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

@app.route('/convert-by-body', methods=['POST'])
def convert_by_body():
    try:
        # Check if file is present in request
        if not request.data:
            return jsonify({'error': 'File data is required in request body'}), 400

        # Get configuration from headers or use defaults
        unwanted_tags = None
        unwanted_attrs = None
        detect_article = request.headers.get('detect-article', 'true').lower() == 'true'
        
        if 'unwanted-tags' in request.headers:
            unwanted_tags = request.headers.get('unwanted-tags').split(',')
            unwanted_tags = [tag.strip() for tag in unwanted_tags if tag.strip()]
        
        if 'unwanted-attrs' in request.headers:
            unwanted_attrs = request.headers.get('unwanted-attrs').split(',')
            unwanted_attrs = [attr.strip() for attr in unwanted_attrs if attr.strip()]

        # Get filename from header or determine extension based on Content-Type
        filename = request.headers.get('filename', '')
        if filename:
            # Use the provided filename to determine extension
            ext = os.path.splitext(filename)[1] or '.bin'
        else:
            # Fallback to Content-Type detection
            content_type = (request.content_type or '').lower()
            ext = '.bin'
            if 'html' in content_type:
                ext = '.html'
            elif 'pdf' in content_type or content_type == 'application/pdf':
                ext = '.pdf'
            elif content_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
                ext = '.docx'
            elif content_type in ['application/vnd.openxmlformats-officedocument.presentationml.presentation', 'application/vnd.ms-powerpoint']:
                ext = '.pptx'
            elif content_type in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel']:
                ext = '.xlsx'
            elif content_type == 'text/csv':
                ext = '.csv'
            elif content_type == 'application/json':
                ext = '.json'
            elif content_type in ['application/xml', 'text/xml']:
                ext = '.xml'
            elif content_type == 'application/epub+zip':
                ext = '.epub'
            elif content_type == 'application/zip':
                ext = '.zip'
            elif content_type.startswith('image/'):
                ext = '.jpg'  # Use .jpg as default for images
            elif content_type.startswith('audio/'):
                ext = '.mp3'  # Use .mp3 as default for audio
            elif content_type == 'text/plain':
                ext = '.txt'
        
        # Check if content is HTML and process it if necessary
        content_to_write = request.data
        if is_html_content(request.data):
            app.logger.info('Detected HTML content, processing it')
            html_content = request.data.decode('utf-8', errors='ignore')
            
            # Extract article content if detect_article flag is set
            if detect_article:
                html_content = extract_article_content(html_content)
            
            cleaned_html = clean_html(html_content, unwanted_tags, unwanted_attrs)
            content_to_write = cleaned_html.encode('utf-8')
            ext = '.html'  # Ensure extension is set to .html

        app.logger.info(f"content to write: {content_to_write}")

        # Create temporary file with uploaded data
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(content_to_write)
            temp_file_path = temp_file.name
        
        try:
            app.logger.info(f"Converting file: {temp_file_path} (ext: {ext})")
            # Convert to markdown
            result = md.convert(temp_file_path)
            app.logger.info(f"markitdown result: {result}")
            markdown_content = result.text_content
            app.logger.info(f"Markdown output: {markdown_content[:200]}")
            
            return jsonify({
                'success': True,
                'markdown': markdown_content
            })
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
    
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

@app.route('/deref', methods=['POST'])
def dereference_url():
    """Dereference a URL by following redirects up to 20 times and return the final URL"""
    try:
        # Get URL from JSON body
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in JSON body'}), 400
        
        url = data['url']
        max_redirects = 20
        redirect_count = 0
        current_url = url
        redirect_chain = [url]
        
        # Configure session with headers to avoid bot detection
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
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
                response = session.get(current_url, allow_redirects=False, timeout=15)
                app.logger.info(f"GET {current_url} -> {response.status_code}")
                app.logger.info(f"Response headers: {dict(response.headers)}")
                
                # Check if this is a redirect response
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get('Location')
                    if location:
                        # Handle relative URLs
                        if location.startswith('/'):
                            from urllib.parse import urljoin
                            current_url = urljoin(current_url, location)
                        elif not location.startswith(('http://', 'https://')):
                            from urllib.parse import urljoin
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
                        app.logger.info(f"Checking for JavaScript redirects in HTML content (length: {len(content)})")
                        
                        # Log a snippet of the content to understand what we're getting
                        content_snippet = content[:500] if len(content) > 500 else content
                        app.logger.info(f"Content snippet: {content_snippet}")
                        
                        # Check if this is a Cloudflare challenge page
                        if 'cf-mitigated' in response.headers.get('cf-mitigated', '') or 'challenge' in content.lower():
                            app.logger.info("Detected Cloudflare challenge page - cannot follow redirect automatically")
                            break
                        
                        # Look for common JavaScript redirect patterns
                        import re
                        js_redirect_patterns = [
                            r'window\.location\.href\s*=\s*["\']([^"\'\']+)["\']',
                            r'window\.location\s*=\s*["\']([^"\'\']+)["\']',
                            r'location\.href\s*=\s*["\']([^"\'\']+)["\']',
                            r'location\s*=\s*["\']([^"\'\']+)["\']',
                            r'document\.location\s*=\s*["\']([^"\'\']+)["\']',
                            r'window\.location\.replace\s*\(\s*["\']([^"\'\']+)["\']\s*\)',
                            r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+url=([^"\'\'\s>]+)',
                            # Additional patterns for beehiiv-style redirects
                            r'location\.replace\s*\(["\']([^"\'\']+)["\']\)',
                            r'window\.open\s*\(["\']([^"\'\']+)["\']',
                            r'href\s*=\s*["\']([^"\'\']+)["\'].*click'
                        ]
                        
                        for pattern in js_redirect_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            if matches:
                                for js_url in matches:
                                    # Skip obviously non-redirect URLs
                                    if any(skip in js_url.lower() for skip in ['javascript:', 'mailto:', '#', 'void(0)']):
                                        continue
                                        
                                    # Handle relative URLs
                                    if js_url.startswith('/'):
                                        from urllib.parse import urljoin
                                        current_url = urljoin(current_url, js_url)
                                    elif not js_url.startswith(('http://', 'https://')):
                                        from urllib.parse import urljoin
                                        current_url = urljoin(current_url, js_url)
                                    else:
                                        current_url = js_url
                                    
                                    app.logger.info(f"Found JavaScript redirect to: {current_url}")
                                    redirect_chain.append(current_url)
                                    redirect_count += 1
                                    break
                            if matches:
                                break
                        else:
                            # No JavaScript redirect found, we're done
                            app.logger.info("No JavaScript redirects found in HTML content")
                            break
                    except Exception as e:
                        app.logger.warning(f"Error parsing JavaScript redirects: {e}")
                        break
                else:
                    # No redirect and not HTML, we're done
                    break
                
            except requests.RequestException as e:
                # If request fails, try HEAD request as fallback
                try:
                    response = session.head(current_url, allow_redirects=False, timeout=10)
                    if response.status_code in [301, 302, 303, 307, 308]:
                        location = response.headers.get('Location')
                        if location:
                            # Handle relative URLs
                            if location.startswith('/'):
                                from urllib.parse import urljoin
                                current_url = urljoin(current_url, location)
                            elif not location.startswith(('http://', 'https://')):
                                from urllib.parse import urljoin
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
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
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
            cleaned_params = {k: v for k, v in query_params.items() 
                            if k.lower() not in tracking_params}
            
            # Rebuild URL with cleaned parameters
            new_query = urlencode(cleaned_params, doseq=True) if cleaned_params else ''
            current_url = urlunparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment
            ))
        
        return jsonify({
            'success': True,
            'original_url': url,
            'final_url': current_url,
            'redirect_count': redirect_count,
            'redirect_chain': redirect_chain,
            'max_redirects_reached': redirect_count >= max_redirects
        })
        
    except Exception as e:
        return jsonify({'error': f'URL dereferencing failed: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # Get Flask configuration from environment variables
    flask_debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    flask_host = os.getenv('FLASK_HOST', '0.0.0.0')
    flask_port = int(os.getenv('FLASK_PORT', '5000'))
    
    app.run(host=flask_host, port=flask_port, debug=flask_debug)
