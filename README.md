# Markdown Converter Service

A Flask-based web service and Apify actors that convert various document formats to Markdown using Microsoft's MarkItDown library. The service provides both REST API endpoints and scalable Apify actors for converting documents from URLs, file uploads, and HTML cleaning.

## Repository Structure

```
markdown-converter/
├── server.py              # Flask server
├── requirements.txt       # Python dependencies for Flask server
├── shared/               # Shared utilities directory
│   ├── utils.py          # Common HTML processing functions
│   ├── browser_utils.py  # Browser automation utilities
│   └── conversion_utils.py # URL dereferencing and conversion logic
├── actors/               # Apify actors directory
│   ├── dereference_url/  # URL dereferencing actor
│   │   ├── main.py       # Python actor implementation
│   │   ├── requirements.txt # Actor dependencies
│   │   └── apify.json    # Actor configuration
│   ├── clean_html/       # HTML cleaning actor
│   │   ├── main.py       # Python actor implementation
│   │   ├── requirements.txt # Actor dependencies
│   │   └── apify.json    # Actor configuration
│   ├── convert_by_url/   # URL to markdown conversion actor
│   │   ├── main.py       # Python actor implementation
│   │   ├── requirements.txt # Actor dependencies
│   │   └── apify.json    # Actor configuration
│   └── convert_by_body/  # Body content to markdown conversion actor
│       ├── main.py       # Python actor implementation
│       ├── requirements.txt # Actor dependencies
│       └── apify.json    # Actor configuration
└── README.md            # This file
```

## Features

- **Multi-format Support**: Convert PDF, DOCX, HTML, and other document formats to Markdown
- **URL-based Conversion**: Convert documents directly from URLs
- **File Upload Conversion**: Upload files via HTTP request body
- **HTML Cleaning**: Clean and sanitize HTML content before conversion
- **AI-Powered Medium.com Support**: Intelligent detection of free reading links using Google Gemini AI
- **Docker Support**: Containerized deployment with Docker and Docker Compose
- **Health Check**: Built-in health monitoring endpoint

## Supported File Formats

- PDF documents
- Microsoft Word documents (.docx)
- HTML files
- And other formats supported by MarkItDown library

## API Endpoints

### 1. Convert by URL

**POST** `/convert-by-url`

Convert a document from a URL to Markdown.

**Request Body:**
```json
{
  "url": "https://example.com/document.pdf"
}
```

**Response:**
```json
{
  "success": true,
  "markdown": "# Document Title\n\nDocument content...",
  "source_url": "https://example.com/document.pdf"
}
```

### 2. Convert by File Upload

**POST** `/convert-by-body`

Convert a document uploaded in the request body to Markdown.

**Headers:**
- `filename` (optional): Original filename to help determine file type
- `Content-Type` (optional): MIME type of the uploaded file

**Request Body:** Binary file data

**Response:**
```json
{
  "success": true,
  "markdown": "# Document Title\n\nDocument content..."
}
```

### 3. Clean HTML

**POST** `/clean-html`

Clean and sanitize HTML content by removing unwanted tags and attributes.

**Request Body:** Raw HTML content

**Response:**
```json
{
  "success": true,
  "html": "<p>Cleaned HTML content</p>"
}
```

### 4. Health Check

**GET** `/health`

Check if the service is running.

**Response:**
```json
{
  "status": "healthy"
}
```

## Apify Actors

This repository also provides four Apify actors that mirror the functionality of the Flask endpoints for scalable, cloud-native processing:

### 1. `dereference_url` Actor

**Purpose**: Dereferences URLs by following redirects and cleaning tracking parameters.

**Input**:
- `url` (string, required): The URL to dereference
- `maxRedirects` (integer, optional): Maximum number of redirects to follow (default: 20)

**Output**:
- `finalUrl`: The final dereferenced URL
- `redirectCount`: Number of redirects followed
- `redirectChain`: Array of all URLs in the redirect chain

**Equivalent Flask endpoint**: `/deref`

### 2. `clean_html` Actor

**Purpose**: Cleans HTML content by removing unwanted tags and attributes.

**Input**:
- `html` (string, required): The HTML content to clean
- `unwantedTags` (array, optional): Tags to remove
- `unwantedAttrs` (array, optional): Attributes to remove
- `detectArticle` (boolean, optional): Extract article content if present

**Output**:
- `cleanedHtml`: The cleaned HTML content
- `originalLength`: Length of original HTML
- `cleanedLength`: Length of cleaned HTML

**Equivalent Flask endpoint**: `/clean-html`

### 3. `convert_by_url` Actor

**Purpose**: Fetches content from a URL and converts it to markdown.

**Input**:
- `url` (string, required): The URL to fetch and convert
- `unwantedTags` (array, optional): HTML tags to remove during cleaning
- `unwantedAttrs` (array, optional): HTML attributes to remove during cleaning
- `detectArticle` (boolean, optional): Extract article content if present

**Output**:
- `markdown`: The converted markdown content
- `sourceUrl`: The final URL after redirects
- `originalUrl`: The original input URL
- `fileExtension`: Detected file extension
- `usedBrowser`: Whether headless browser was used

**Equivalent Flask endpoint**: `/convert-by-url`

### 4. `convert_by_body` Actor

**Purpose**: Converts content from request body to markdown.

**Input**:
- `content` (string): Text content to convert (use this OR base64Content)
- `base64Content` (string): Base64 encoded content for binary files
- `contentType` (string, optional): MIME type of the content
- `filename` (string, optional): Original filename
- `unwantedTags` (array, optional): HTML tags to remove during cleaning
- `unwantedAttrs` (array, optional): HTML attributes to remove during cleaning
- `detectArticle` (boolean, optional): Extract article content if present

**Output**:
- `markdown`: The converted markdown content
- `fileExtension`: Detected file extension
- `contentType`: Original content type
- `wasBase64`: Whether input was base64 encoded

**Equivalent Flask endpoint**: `/convert-by-body`

### Apify Actor Setup

#### Prerequisites

1. **Apify Account**: Sign up at [apify.com](https://apify.com)
2. **Apify CLI**: Install the Apify CLI
   ```bash
   npm install -g apify-cli
   ```
3. **Login**: Authenticate with your Apify account
   ```bash
   apify login
   ```

#### Deploying Individual Actors

Each actor can be deployed independently:

```bash
# Navigate to the specific actor directory
cd actors/dereference_url

# Initialize and deploy
apify push
```

Repeat for each actor:
- `actors/dereference_url`
- `actors/clean_html`
- `actors/convert_by_url`
- `actors/convert_by_body`

#### Using Apify Actors

**Via Apify Console**:
1. Go to [console.apify.com](https://console.apify.com)
2. Navigate to your deployed actor
3. Click "Try it" and provide input JSON
4. Run the actor and view results

**Via API**:
```javascript
const response = await fetch('https://api.apify.com/v2/acts/YOUR_USERNAME~convert-by-url/runs', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer YOUR_API_TOKEN',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        url: 'https://example.com/article'
    })
});
```

**Via Apify SDK**:
```javascript
import { ApifyApi } from 'apify-client';

const client = new ApifyApi({ token: 'YOUR_API_TOKEN' });
const run = await client.actor('YOUR_USERNAME/convert-by-url').call({
    url: 'https://example.com/article'
});
```

## Installation

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Local Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd markdown-converter
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python server.py
```

The service will be available at `http://localhost:5000`

### Docker Installation

#### Using Docker

1. Build the Docker image:
```bash
docker build -t markdown-converter .
```

2. Run the container:
```bash
docker run -p 5000:5000 markdown-converter
```

#### Using Docker Compose

1. Copy the environment template and configure:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:
```bash
# Required for AI-powered Medium.com features
GEMINI_API_KEY=your_actual_api_key_here

# Optional: Customize other settings
FLASK_DEBUG=false
FLASK_PORT=5000
```

3. Start the service:
```bash
docker-compose up -d
```

4. Stop the service:
```bash
docker-compose down
```

## Usage Examples

### Convert PDF from URL

```bash
curl -X POST http://localhost:5000/convert-by-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/document.pdf"}'
```

### Upload and Convert File

```bash
curl -X POST http://localhost:5000/convert-by-body \
  -H "filename: document.pdf" \
  --data-binary @document.pdf
```

### Clean HTML Content

```bash
curl -X POST http://localhost:5000/clean-html \
  -H "Content-Type: text/html" \
  --data-binary @document.html
```

### Health Check

```bash
curl http://localhost:5000/health
```

## AI-Powered Medium.com Support

This service includes intelligent detection of free reading links for Medium.com articles using Google Gemini AI.

### Setup Gemini AI (Required for Medium.com)

1. **Get API Key**: Visit [Google AI Studio](https://aistudio.google.com/) and create a free API key
2. **Configure Environment**: Add your API key to the `.env` file:
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   ```
3. **Verify Setup**: Run the test script:
   ```bash
   python test_gemini_config.py
   ```

### How It Works

- **AI Analysis**: Gemini AI analyzes HTML content to find free reading links
- **Pattern Detection**: Looks for Medium friend links (`sk=` parameters) and free access URLs
- **Fallback Support**: Falls back to regex patterns if AI is unavailable
- **Enhanced Accuracy**: Much better detection compared to regex-only approaches

### Supported Medium Sites

- medium.com (all publications)
- levelup.gitconnected.com
- towardsdatascience.com
- betterprogramming.pub
- javascript.plainenglish.io
- python.plainenglish.io
- blog.devgenius.io
- codeburst.io
- hackernoon.com

### Example: Convert Medium Article

```bash
curl -X POST http://localhost:5000/convert-by-url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://levelup.gitconnected.com/some-article"}'
```

**Note**: Without Gemini API key, the system will still work but with limited Medium.com support using regex patterns only.

## Dependencies

- **Flask**: Web framework for creating the REST API
- **MarkItDown**: Microsoft's library for converting documents to Markdown
- **Requests**: HTTP library for downloading files from URLs
- **BeautifulSoup4**: HTML parsing and cleaning
- **Werkzeug**: WSGI utilities for secure filename handling
- **lxml**: XML and HTML processing
- **pypdf2**: PDF processing support
- **python-docx**: Microsoft Word document support

## HTML Cleaning Features

The service includes intelligent HTML cleaning that:

- Removes unwanted tags: `head`, `img`, `script`, `style`, `meta`, `link`, `noscript`, `iframe`, `embed`, `object`
- Strips unwanted attributes: `style`, `class`, `id`, `onclick`, event handlers, data attributes
- Removes empty tags that don't contain meaningful content
- Preserves essential HTML structure for proper Markdown conversion

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `400 Bad Request`: Missing required parameters or invalid input
- `500 Internal Server Error`: Conversion failures or server errors

Error responses include descriptive messages:
```json
{
  "error": "Conversion failed: [specific error message]"
}
```

## Configuration

### Environment Variables

The service can be configured using environment variables. Copy `.env.example` to `.env` and customize as needed:

```bash
cp .env.example .env
```

**Required Variables:**
- **GEMINI_API_KEY**: Google AI Studio API key for AI-powered Medium.com features

**Optional Variables:**
- **FLASK_HOST**: Host address (default: `0.0.0.0`)
- **FLASK_PORT**: Port number (default: `5000`)
- **FLASK_DEBUG**: Debug mode (default: `true` for development, set to `false` for production)

**AI Features:**
To enable AI-powered Medium.com free reading link detection:
1. Get an API key from [Google AI Studio](https://aistudio.google.com/)
2. Set `GEMINI_API_KEY` in your `.env` file
3. The service will automatically use AI when processing Medium.com URLs

**Docker Deployment:**
When using Docker Compose, the `.env` file is automatically loaded and environment variables are passed to the container.

### Production Deployment

For production deployment:

1. Set `debug=False` in the Flask app configuration
2. Use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 server:app
```
3. Configure reverse proxy (nginx/Apache) for SSL termination
4. Set up proper logging and monitoring

## Logging

The application includes logging for:
- HTML content detection and cleaning
- File conversion processes
- Error tracking and debugging

## Security Considerations

- File uploads are processed in temporary files that are automatically cleaned up
- HTML content is sanitized to remove potentially malicious scripts and styles
- Secure filename handling prevents directory traversal attacks
- No persistent file storage reduces attack surface

## Limitations

- Maximum file size depends on available memory and Flask configuration
- Some complex document formats may not convert perfectly
- Network timeouts may occur for large files downloaded from URLs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Check the application logs for error details
- Verify that all dependencies are properly installed
- Ensure the service is accessible on the configured port
- Test with the health check endpoint first