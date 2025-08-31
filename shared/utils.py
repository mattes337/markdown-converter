#!/usr/bin/env python3
"""
Shared utility functions for HTML processing and content cleaning.
Used by both Flask server and Apify actors.
"""

import re
from bs4 import BeautifulSoup


def is_html_content(content):
    """Check if content is HTML by looking for HTML tags"""
    if isinstance(content, bytes):
        content_str = content.decode('utf-8', errors='ignore')
    else:
        content_str = str(content)
    return bool(re.search(
        r'<\s*html[^>]*>|<\s*body[^>]*>|<\s*div[^>]*>|<\s*p[^>]*>',
        content_str, re.IGNORECASE
    ))


def extract_article_content(html_content):
    """Extract content from <article> tag if present, otherwise return original content"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Look for article tag
    article = soup.find('article')
    if article:
        return str(article)

    # If no article tag found, return the original content
    return html_content


def clean_html(html_content, unwanted_tags=None, unwanted_attrs=None):
    """Clean HTML content by removing unwanted tags and attributes"""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Default unwanted tags if not provided
    if unwanted_tags is None:
        unwanted_tags = [
            'head', 'img', 'script', 'style', 'meta', 'link',
            'noscript', 'iframe', 'embed', 'object'
        ]

    # Default unwanted attributes if not provided
    if unwanted_attrs is None:
        unwanted_attrs = [
            'style', 'class', 'id', 'onclick', 'onload', 'onerror',
            'data-(.*)', 'width', 'height', 'valign', 'role',
            'align', 'cellspacing', 'border', 'cellpadding', 'aria-(.*)'
        ]

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
        if (not tag.get_text(strip=True) and not tag.find_all()
                and tag.name not in ['br', 'hr', 'img']):
            tag.decompose()

    return str(soup)