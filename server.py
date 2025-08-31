# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
import os
import logging
from werkzeug.utils import secure_filename
from shared.utils import is_html_content, extract_article_content, clean_html
from shared.conversion_utils import dereference_url, convert_url_to_markdown, convert_body_to_markdown
from shared.browser_utils import fetch_with_browser_fallback

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

# All utility functions moved to shared modules

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
        
        # Use shared conversion utility
        result = convert_url_to_markdown(url, unwanted_tags, unwanted_attrs, detect_article)
        return jsonify(result)
    
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

        # Get filename from header
        filename = request.headers.get('filename', '')
        content_type = request.content_type or ''
        
        # Use shared conversion utility
        result = convert_body_to_markdown(request.data, filename, content_type, unwanted_tags, unwanted_attrs, detect_article)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'Conversion failed: {str(e)}'}), 500

@app.route('/deref', methods=['POST'])
def dereference_url_endpoint():
    """Dereference a URL by following redirects up to 20 times and return the final URL"""
    try:
        # Get URL from JSON body
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required in JSON body'}), 400
        
        url = data['url']
        
        # Use shared dereference utility
        result = dereference_url(url)
        return jsonify(result)
        
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
