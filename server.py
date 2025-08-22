from flask import Flask, request, jsonify
import requests
import tempfile
import os
import re
import time
import random
from markitdown import MarkItDown
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup


app = Flask(__name__)

# Initialize MarkItDown
md = MarkItDown()


def is_html_content(content):
    """Check if content is HTML by looking for HTML tags"""
    content_str = content.decode('utf-8', errors='ignore') if isinstance(content, bytes) else str(content)
    return any(tag in content_str.lower() for tag in ['<html', '<body', '<div', '<p', '<span', '<!doctype'])

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
        
        # Download the file from URL with browser-like headers to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'cross-site',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
        }
        
        # Create a session to maintain cookies
        session = requests.Session()
        session.headers.update(headers)
        
        # Add a small random delay to appear more human-like
        time.sleep(random.uniform(0.5, 2.0))
        
        # Add timeout and allow redirects
        response = session.get(url, stream=True, timeout=30, allow_redirects=True)
        
        # Check for common bot detection responses
        if response.status_code == 403:
            # Try with a different user agent if we get 403
            alternative_headers = headers.copy()
            alternative_headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
            session.headers.update(alternative_headers)
            time.sleep(random.uniform(1.0, 3.0))
            response = session.get(url, stream=True, timeout=30, allow_redirects=True)
        
        response.raise_for_status()
        
        # Determine file extension from URL or Content-Type
        ext = '.bin'
        if url.lower().endswith('.html'):
            ext = '.html'
        elif url.lower().endswith('.pdf'):
            ext = '.pdf'
        elif 'html' in response.headers.get('content-type', '').lower():
            ext = '.html'
        
        # Read content
        file_content = b''
        for chunk in response.iter_content(chunk_size=8192):
            file_content += chunk
        
        # Check if content is HTML and clean it if necessary
        content_to_write = file_content
        if ext == '.html' or is_html_content(file_content):
            app.logger.info('Detected HTML content from URL, cleaning it')
            html_content = file_content.decode('utf-8', errors='ignore')
            cleaned_html = clean_html(html_content, unwanted_tags, unwanted_attrs)
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
        
        # Provide more specific error messages for common bot detection scenarios
        if '403' in error_msg or 'Forbidden' in error_msg:
            error_msg = f'Access forbidden (403) - The server may be blocking automated requests. Original error: {error_msg}'
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
            content_type = request.content_type or ''
            ext = '.bin'
            if 'html' in content_type:
                ext = '.html'
            elif 'pdf' in content_type:
                ext = '.pdf'
            # Add more types as needed
        
        # Check if content is HTML and clean it if necessary
        content_to_write = request.data
        if is_html_content(request.data):
            app.logger.info('Detected HTML content, cleaning it')
            html_content = request.data.decode('utf-8', errors='ignore')
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

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
