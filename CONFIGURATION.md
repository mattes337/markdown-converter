# Configurable HTML Cleaning

The markdown converter now supports configurable unwanted tags and attributes removal with regex pattern matching support.

## Features

- **Configurable unwanted tags**: Specify which HTML tags to remove completely
- **Configurable unwanted attributes**: Specify which attributes to remove from all tags
- **Regex pattern matching**: Use regex patterns to match multiple tags or attributes at once
- **REST API integration**: Pass configuration via HTTP headers or JSON body

## Usage

### Default Behavior

By default, the following tags and attributes are removed:

**Default unwanted tags:**
- `head`, `img`, `script`, `style`, `meta`, `link`, `noscript`, `iframe`, `embed`, `object`

**Default unwanted attributes:**
- `style`, `class`, `id`, `onclick`, `onload`, `onerror`, `data-(.*)`, `width`, `height`, `valign`, `role`, `align`, `cellspacing`, `border`, `cellpadding`, `aria-(.*)`

### Configuring via HTTP Headers

For `/clean-html` and `/convert-by-body` endpoints, pass configuration via headers:

```bash
curl -X POST http://localhost:5000/clean-html \
  -H "Content-Type: text/html" \
  -H "unwanted-tags: script,style,custom-(.*)" \
  -H "unwanted-attrs: data-(.*),aria-(.*),onclick" \
  --data-raw "<html>...</html>"
```

### Configuring via JSON Body

For `/convert-by-url` endpoint, pass configuration in JSON body:

```bash
curl -X POST http://localhost:5000/convert-by-url \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/page.html",
    "unwanted_tags": ["script", "style", "custom-(.*)"],
    "unwanted_attrs": ["data-(.*)", "aria-(.*)", "onclick"]
  }'
```

## Regex Pattern Matching

### Tags

You can use regex patterns to match multiple tags:

- `custom-(.*)` - Matches any tag starting with "custom-" (e.g., `custom-button`, `custom-widget`)
- `h[1-6]` - Matches heading tags h1 through h6
- `.*-component` - Matches any tag ending with "-component"

### Attributes

You can use regex patterns to match multiple attributes:

- `data-(.*)` - Matches all data attributes (e.g., `data-id`, `data-value`, `data-test`)
- `aria-(.*)` - Matches all ARIA attributes (e.g., `aria-label`, `aria-hidden`, `aria-expanded`)
- `on(.*)` - Matches all event handler attributes (e.g., `onclick`, `onload`, `onmouseover`)

## Examples

### Remove All Data Attributes

```bash
# Via headers
curl -X POST http://localhost:5000/clean-html \
  -H "unwanted-attrs: data-(.*)" \
  --data-raw "<div data-id='123' data-value='test'>Content</div>"

# Result: <div>Content</div>
```

### Remove Custom Components

```bash
# Via headers
curl -X POST http://localhost:5000/clean-html \
  -H "unwanted-tags: custom-(.*),app-(.*)" \
  --data-raw "<div><custom-button>Click</custom-button><app-header>Title</app-header></div>"

# Result: <div></div>
```

### Remove Specific Attributes Only

```bash
# Via headers
curl -X POST http://localhost:5000/clean-html \
  -H "unwanted-attrs: style,class,onclick" \
  --data-raw '<p style="color:red" class="text" onclick="alert()" id="para">Text</p>'

# Result: <p id="para">Text</p>
```

## API Endpoints

### POST /clean-html

Cleans HTML content and returns the cleaned HTML.

**Headers:**
- `unwanted-tags`: Comma-separated list of tag patterns to remove
- `unwanted-attrs`: Comma-separated list of attribute patterns to remove

### POST /convert-by-body

Converts uploaded content to markdown with HTML cleaning.

**Headers:**
- `unwanted-tags`: Comma-separated list of tag patterns to remove
- `unwanted-attrs`: Comma-separated list of attribute patterns to remove

### POST /convert-by-url

Downloads content from URL and converts to markdown with HTML cleaning.

**JSON Body:**
```json
{
  "url": "https://example.com/page.html",
  "unwanted_tags": ["script", "style", "custom-(.*)"],
  "unwanted_attrs": ["data-(.*)", "aria-(.*)", "onclick"]
}
```

## Notes

- Regex patterns are compiled using Python's `re` module
- Patterns use `.*` for wildcard matching (converted from `*` for convenience)
- Empty or whitespace-only configuration values are ignored
- If no configuration is provided, default values are used
- Invalid regex patterns will cause the cleaning to fail with an error