# DryDev Search to Markdown Actor

This Apify actor searches Google using the Google SERP proxy and converts the resulting web pages to Markdown format.

## Features

- **Google Search Integration**: Uses Apify's Google SERP proxy to perform direct searches
- **Recent Content Filtering**: Option to prioritize recently published content
- **Batch Processing**: Scrapes and converts multiple URLs from search results
- **Markdown Conversion**: Converts web page content to clean Markdown format
- **HTML Cleaning**: Removes unwanted HTML tags and attributes
- **Error Handling**: Robust error handling for failed conversions

## Input Parameters

### Required
- `searchQuery` (string): The search query to execute on Google

### Optional
- `maxResults` (integer, default: 5): Number of web pages to scrape and convert (1-20)
- `getRecent` (boolean, default: false): If true, prioritize recently published content
- `countryCode` (string, default: "US"): Two-letter country code for search localization (e.g., US, UK, DE, FR)
- `languageCode` (string, default: "en"): Two-letter language code for search results (e.g., en, es, fr, de)
- `unwantedTags` (array): HTML tag names to remove during cleaning
- `unwantedAttrs` (array): HTML attribute names to remove during cleaning

## Output Format

The actor outputs an array of objects, one for each processed web page:

```json
{
  "markdown": "# Page Title\n\nPage content in markdown...",
  "url": "https://example.com/page",
  "title": "Page Title",
  "publish_date": null,
  "snippet": "Search result snippet",
  "success": true,
  "error": null
}
```

## Usage Examples

### Basic Search
```json
{
  "searchQuery": "python web scraping tutorial",
  "maxResults": 5
}
```

### Recent Content Search
```json
{
  "searchQuery": "artificial intelligence trends 2024",
  "maxResults": 10,
  "getRecent": true
}
```

### Localized Search
```json
{
  "searchQuery": "machine learning guide",
  "maxResults": 5,
  "countryCode": "DE",
  "languageCode": "de"
}
```

### Custom HTML Cleaning
```json
{
  "searchQuery": "machine learning guide",
  "maxResults": 3,
  "countryCode": "US",
  "languageCode": "en",
  "unwantedTags": ["script", "style", "nav", "footer", "aside"],
  "unwantedAttrs": ["class", "id", "style", "onclick"]
}
```

## Environment Variables

### Required
- `APIFY_PROXY_PASSWORD`: Your Apify proxy password (found at https://console.apify.com/proxy)

## Dependencies

- **Apify SDK**: For actor framework
- **Requests**: For HTTP requests through Google SERP proxy
- **BeautifulSoup4**: For HTML parsing and search result extraction
- **Shared Utilities**: Uses the project's shared conversion utilities
- **MarkItDown**: For HTML to Markdown conversion
- **Playwright**: For JavaScript-heavy websites

## Error Handling

The actor handles various error scenarios:
- Invalid search queries
- Network timeouts
- Failed URL conversions
- Rate limiting
- Invalid HTML content

Failed conversions are marked with `success: false` and include error details.

## Rate Limiting

Be mindful of:
- Google SERP proxy request limits
- Target website rate limiting
- Apify platform limits

Consider adding delays between requests for large batch operations.

## Development

To test the actor locally:

1. Set up Apify credentials: `export APIFY_TOKEN=your_token`
2. Set up proxy password: `export APIFY_PROXY_PASSWORD=your_proxy_password`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the test script: `python ../../../test_search_to_markdown_actor.py`

## Notes

- The actor requires a valid Apify proxy password for Google SERP proxy access
- Some websites may block automated scraping
- Large `maxResults` values may take significant time to process
- The `getRecent` parameter uses Google's time-based filtering (last month)
- Proxy requests are charged based on the number of requests made